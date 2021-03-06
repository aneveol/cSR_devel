
"""Module for handing, manipulating and inspecting data.
"""

from csr import Preprocess

import operator
import random
try:
    import ujson as json
except ImportError:
    import json

def parse_condition(row_condition):
    """Parses the given condition string into a condition that can be used with `DataStream#select` and `DataStream#select_indices`.

    Args:
        row_condition (str): A string on the form COL=VALUE or COL!=VALUE

    Raises:
        ValueError: If `row_condition` is not in the correct format

    """
    # Case 1: inequality
    tokens = row_condition.split('!=')
    if len(tokens) == 2:
        k, v = tokens
        return (lambda row: row[k] != v)
    # Case 2: equality
    tokens = row_condition.split('=')
    if len(tokens) == 2:
        k, v = tokens
        return (lambda row: row[k] == v)
    
    raise ValueError("Expression %s is not a condition" % row_condition)

def parse_conditions(row_conditions):
    """Helper function to avoid frequent and long list comps.
    Applies parse_condition to each element in `row_conditions`

    Args:
        row_conditions (list of str): List of row conditions

    See Also:
        parse_condition

    Note:
        Deprecated and may be removed in future versions
    """
    return [parse_condition(cond) for cond in row_conditions]

class DataStream(object):
    """Simple decorator class to facilitate data handling and passing data from
    stage to stage during data processing, without having to care about
    how the data is handled.
    The internal data structure is intended to be marshallable into
    human-readable standard output.
    """
    class _DataRow(object):
        """
        Decorator over dicts.
        """
        def __init__(self, header, entries):
            # Catch-22 situation where __setattr__ can only be called once we
            # have set the 'data' variable, but we need to invoke __setattr__
            # to set instance variables. Resolve by instead invoking super
            object.__setattr__(self, 'data', {})
            object.__setattr__(self, 'header', header)
            for title, entry in zip(header, entries):
                self.data[title] = entry
        def add_column(self, name, value):
            self.data[name] = value
        def __getitem__(self, name):
            return self.data[name]
        def __setitem__(self, name, value):
            self.data[name] = value
        def __getattr__(self, name):
            if name in object.__getattribute__(self, 'data').keys():
                return object.__getattribute__(self, 'data')[name]
            else:
                # This requires us to inherit from object in 2.x (but not
                # in 3.x). Caveats abound...
                return object.__getattribute__(self, name)
        def __setattr__(self, name, value):
            if name in self.data.keys():
                self[name] = value
            else:
                # This requires us to inherit from object in 2.x (but not
                # in 3.x). Caveats abound...
                return object.__setattr__(self, name, value)
        def copy(self):
            entries = [self.data[col] for col in self.header]
            return DataStream._DataRow(self.header, entries)
    
    def __init__(self, *header):
        """Construct an empty DataStream with header `header`
        
        Args:
            header: The items to use as the header
        """
        if len(header) > len(set(header)):
            raise ValueError("Header elements must be unique")
        # See _DataRow#__init_
        object.__setattr__(self, 'data', [])
        object.__setattr__(self, 'header', header)

    def append(self, row):
        """ Add the given row to the data stream

        Args:
            row (list): The row items to append

        Returns:
            self

        Raises:
            ValueError: If `row` is not the same length as the datastream header
        """
        if len(self.header) != len(row):
            raise ValueError("Data length to append does not match format of datastream")
        self.data.append(DataStream._DataRow(self.header, row))
        return self

    def has_column(self, col):
        """Check if the given column name exists in the datastream header

        Args:
            col (str): The column name to check for

        Returns:
            True if column exists, else False
        """
        return col in self.header
    
    def add_column(self, col, default_value = None):
        """Adds the specified column to the datastream, initialized to `default_value`. Resets the column values to `default_value` if the column already exists.

        Args:
            col (str): The column name to add
            default_value: The initial value for the column

        Returns:
            self
        """
        if col in self.header:
            for row in self:
                row[col] = default_value
            return self
        self.header = self.header + (col,)
        for row in self:
            row.add_column(col, default_value)
        return self

    def delete_if(self, func):
        """Deletes all rows in the datastream for which `func` returns truthy values.

        Args:
            func (callable): A functor that takes data rows, and returns boolean values

        Returns:
            self
        """
        self.data = [x for x in self.data if not func(x)]
        return self

    # We might want to restricts the types we handle to
    # e.g. str, int, and lists to improve the intuitiveness
    # and the error handling. Currently error messages for
    # missing headers are cryptic
    def __getitem__(self, ind):
        # Retrieve by column
        if type(ind) == str:
            if ind in self.header:
                return [x[ind] for x in self.data]
            else: raise ValueError("Trying to access non-existant field '%s' in DataStream" % ind)
        
        try:
            # Check if ind is arraylike
            ret_val = DataStream(*self.header)
            # Logical indexing
            if (len(ind) == len(self)) and all([isinstance(i, bool) for i in ind]):
                for i, select in enumerate(ind):
                    if select:
                        ret_val.append([self.data[i][col] for col in self.header])
            else: # Try treating ind as a list of indices
                for i in ind:
                    ret_val.append([self.data[i][col] for col in self.header])
            return ret_val
        except: pass
        
        # Single index, numeric
        return self.data[ind]

    def __getattr__(self, name):
        if name == 'shape': return (len(self.data), len(self.header))
        # Retrieve by column
        elif name in object.__getattribute__(self, 'header'):
            return [x[name] for x in object.__getattribute__(self, 'data')]
        else:
            # This requires us to inherit from object in 2.x (but not
            # in 3.x). Caveats abound...
            return object.__getattribute__(self, name)
    
    def __setattr__(self, name, rval):
        # Assign whole column
        if name in self.header:
            assert len(self.data) == len(rval)
            for x, value in zip(self.data, rval):
                setattr(x, name, value)
        else:
            # This requires us to inherit from object in 2.x (but not
            # in 3.x). Caveats abound...
            return object.__setattr__(self, name, rval)

    def merge(self, other):
        """Add all data from `other` to this datastream. Requires `other` to include all columns in this datastream. Extra columns in `other` are ignored.
        
        Args:
            other (DataStream): datastream of data to add
        
        Returns:
            self

        Raises:
            ValueError: if `other` is not a DataStream object
            ValueError: if the headers of the two datastreams differ
        """
        if type(other) != DataStream:
            msg = 'Trying to add object of type %s to DataStream'
            raise ValueError(msg % type(other))
        if not set(self.header).issubset(set(other.header)):
            msg = 'Failed to merge data streams, mismatched headers [%s] is not a subset of [%s]'
            raise ValueError(msg % (', '.join(self.header), ', '.join(other.header)))
        for row in other.data:
            # Retain header order of self
            # Ignore extraneous columns
            values = [row[col] for col in self.header]
            self.data.append(DataStream._DataRow(self.header, values))
        return self

    @classmethod
    def parse(self, raw_data):
        """Parse input data in marshalled string format, and return a DataStream object.
        
        Args:
            raw_data (str): Data to unmarshall.
        
        Returns:
            A DataStream object corresponding to the data
        """
        # Assume that the input is unmarshalled data of some kind that
        # can be parsed by json
        tmp = json.loads(raw_data)
        ret_val = DataStream(*tmp["header"])
        for row in tmp["data"]:
            ret_val.append(row)
        return ret_val

    def __iter__(self):
        """
        Iterator method
        Returns an iterator over the data collection, in which each
        iteration yields a dict of header-value pairs for the current
        data row.
        """
        return self.data.__iter__()
    
    def __len__(self): return len(self.data)

    def __str__(self):
        return ('DataStream[%s] x %i' % (', '.join(self.header), len(self)))

    def select_indices(self, row_conditions):
        """Returns the row indices for which all `row_conditions` evaluate true.
        
        See Also:
            select_indices, parse_condition, parse_conditions
        
        Args:
            row_conditions (list of functors): Conditions to apply
        
        Returns:
            List indices where the conditions are true
        """
        indices = []
        i = 0
        for row in self:
            if all([cond(row) for cond in row_conditions]):
                indices.append(i)
            i += 1
        return indices
    
    def select(self, row_conditions):
        """Returns the rows for which all `row_conditions` evaluate true.
        
        See Also:
            select_indices, parse_condition, parse_conditions
        
        Args:
            row_conditions (list of functors): Conditions to apply
        
        Returns:
            List of data rows where the conditions are true
        """
        return self[self.select_indices(row_conditions)]
    
    def sort(self, key, reverse = False):
        """Sort the datastream in place. Note that sorted(DataStream) returns a list of _DataRows
        and not a DataStream instance.
        
        Args:
            key: see definition of sorted
            reverse (boolean): True to sort descending
        
        Returns:
            self
        """
        self.data = sorted(self.data, key=key, reverse = reverse)
        return self

    def marshall(self):
        """Marshall the data to string format. The resulting data can be unmarshalled using `DataStream#parse`
        
        Returns:
            A marshalled representation of the data
        """
        data = []
        for row in self.data:
            data.append([row[col] for col in self.header])
        return json.dumps({"header": self.header, "data": data})

# TODO: implement some kind of override that can handle out of place sort
# def sorted(): ...

# Data inspection and manipulation
if __name__ == "__main__":
    import sys
    import argparse
    
    parser = argparse.ArgumentParser(description="""
    Module for data handing, manipulation and inspection.

    When run on the command line, the module takes a datastream (json) file as input, performs the specified operations and outputs the results. Input and output defaults to stdin and stdout if no file paths are specified.

    The results are normally a marshalled, machine readable defition of the data. To use human readable output, add the flag '--inspect'.
    """,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--input',   nargs  = '*', type = argparse.FileType('r'),
                        default = sys.stdin,
                        help = 'File path to the data file to process. Defaults to stdin.'
    )
    parser.add_argument('--output',  nargs  = '?', type = argparse.FileType('w'),
                        default = sys.stdout,
                        help = 'File path where the resuls should be written. defaults to stdout.'
    )
    parser.add_argument('--inspect', action = 'store_true', help = 'Toggle human/machine readable output')
    parser.add_argument('--full',    action = 'store_true', help = 'Disable column truncation')
    parser.add_argument('--set',     nargs  = '+', help = 'Assignment operations to perform on all rows. Takes the form COL=VALUE')
    parser.add_argument('--get',     nargs  = '+', help = 'Restrict selection to rows for which the condition holds. Takes the form COL=VALUE')
    parser.add_argument('--sort',    nargs  = '?', type = str, help = "Column to sort output on. End with a hyphen/minus for descending order.")
    parser.add_argument('--col',     nargs  = '+', help = 'Restrict output to the given columns only')
    parser.add_argument('--select',  nargs  = '?', type = int, help = 'Restrict output to the first N rows only')

    args = parser.parse_args()
    
    # TODO check sanity of input args

    d = None
    for input_file in args.input:
        # Ugly, can we ducktype somehow?
        d_i = DataStream.parse(isinstance(input_file, str) and input_file
                               or input_file.read())
        if not d:
            d = d_i
        else:
            if not set(d.header).issubset(set(d_i.header)):
                missing = set(d.header) - set(d_i.header)
                raise ValueError("Missing columns in input file: [%s]" % (', '.join(missing)))
            d.merge(d_i)
    
    cols = args.col and args.col or d.header
    row_conditions = args.get and args.get or []
    row_conditions = parse_conditions(row_conditions)
    '''
    row_conditions = [cond.split('=') for cond in row_conditions]
    if any([len(tokens) != 2 for tokens in row_conditions]):
        raise ValueError("Expression is not a condition")
    # We need to give k, v their own scope
    def make_cond(k, v): return lambda row: row[k] == v
    row_conditions = [make_cond(k, v) for k, v in row_conditions]
    # This does not work since k, v in the lambda will get bound to the variables
    # and not their values in each iteration:
    # row_conditions = [lambda row: row[k] == v for k, v in row_conditions]
    '''
    d_temp = d
    d = DataStream(*cols)
    for row in d_temp:
        if all([cond(row) for cond in row_conditions]):
            d.append([row[c] for c in cols])
    
    if args.select:
        ind = range(len(d))
        ind = ind[:args.select]
        d = d[ind]

    if args.set:
        for cmd in args.set:
            tokens = cmd.split('=')
            if len(tokens) != 2:
                raise ValueError("Expression is not an assignment: %s" % cmd)
            col = tokens[0].strip()
            value = tokens[1].strip()
            if not d.has_column(col): d.add_column(col)
            setattr(d, col, [value] * len(d))
    
    if args.sort:
        if args.sort.endswith('-'):
            d.sort(lambda row: float(row[args.sort[:-1]]), reverse = True)
        else:
            d.sort(lambda row: float(row[args.sort]))
    
    if args.inspect:
        d = Preprocess.clean_text(d)
        
        max_w = 40
        table = [d.header]
        # Make divider
        table.append(["="*len(h) for h in d.header])
        for row in d.data:
            table.append([row[col] for col in d.header])
        # zip(*arg) takes the transpose
        def compose2(f, g): return lambda *a, **kw: f(g(*a, **kw)) # Not in vanilla python
        widths = [max(map(compose2(len, str), col)) for col in zip(*table)]
        widths = [min(w, max_w) for w in widths]
        for row in table:
            adj_row = []
            for w, x in zip(widths, map(str, row)):
                # Pad to w
                x = x + ' '*(w-len(x))
                # Truncate if longer than max_w
                if not args.full and len(x) > max_w: x = ("%s..." % x[0:max_w-3])
                adj_row.append(x)
            args.output.write(' '.join(adj_row))
            args.output.write('\n')
        args.output.write('--------\n')
        args.output.write('%i rows\n' % len(d))
    else:
        args.output.write(d.marshall())
        args.output.write('\n')

