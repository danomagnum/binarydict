import struct
from collections import OrderedDict

# Provide easier to use definitions of the constants the struct module uses.
# See https://docs.python.org/3/library/struct.html
CHAR = 'c'
SINT8 = 'b'
UINT8 = 'B'
BOOL = '?'
SINT16 = 'h'
UINT16 = 'H'
SINT32 = 'l'
UINT32 = 'L'
SINT64 = 'q'
UINT64 = 'Q'
SINT_NATIVE = 'n'
UINT_NATIVE = 'N'
HALF = 'e'
FLOAT = 'f'
DOUBLE = 'd'


def STRING(count):
    '''
    Per the struct module you can prepend a type with a count to have repeats.  It really only applies to what
    we are doing here when we have a string or padding bytes.  So the STRING and SPARE "types" take a length argument.
    I see no reason to complicate this by making it a StructObject
    :param count: how long the string is in bytes
    :return: the equivalent struct module string
    '''
    return '{}s'.format(count)


class StructObject(object):
    '''
    Complex data such as arrays and nested structs need to have a little wits about them.  This object is the
    template for classes that provide those wits.
    '''
    def get_format(self):
        '''
        :return: This should return the struct module string that allows the data for this object to be pulled
        out of a byte stream
        '''
        return ''

    def parse_unpacked(self, unpacked_data):
        '''
        hopefully I cna make this unpack generic enough to use for other things than arrays at some point
        :param unpacked_data: a python list of the unpacked elements
        :return: (value, number of items used from list)
        '''

        return 0, 0

    def create_packlist(self, value):
        '''
        :return: Returns a list that gets combined onto the end of the current list to be packed.
         It should match the format returned by get_format
        '''
        return []

class SPARE(StructObject):
    '''
    This StructObject provides a way to add "padding" bytes to your structure.
    '''
    def __init__(self, length):
        '''

        :param length: how many bytes of padding to use
        '''
        self.length = length

    def get_format(self):
        'format for spare bytes is an x.  preceding it with the number here to ignore the right amount'
        return '{}x'.format(self.length)

    def parse_unpacked(self, unpacked_data):
        '''
        Because this is a padding value, we will return that we took 0 elements off the unpack_data list.
        and we'll return None as our value
        :param unpacked_data: a python list of the unpacked elements
        :return: value, number of items used from list
        '''
        return None, 0

    def create_packlist(self, value):
        '''
        in this case we return nothing because this is padding and no values need to end up converted
        to bytes
        :return: returns a list that gets combined onto the end of the current list to be packed.
         It should match the format returned by get_format
        '''
        return []


class ARRAY(StructObject):
    def __init__(self, data_type, length):
        '''
        Structure object for creating arrays.  These map to python lists
        :param data_type: one of the ALLCAPS data types at the top of the file
        :param length: how many elements the array contains
        '''
        self.data_type = data_type
        self.length = length

    def get_format(self):
        '''
        :return:
        The format here is just "<# of elements><element type>"
        '''
        #TODO: support complex nested data types here
        if isinstance((self.data_type), StructObject):
            format_str = self.data_type.get_format() * self.length
            return format_str
        else:
            return f'{self.length}{self.data_type}'

    def parse_unpacked(self, unpacked_data):
        '''
        In the case of the array we will take the first <self.length> items from the unpacked data list
        and let the caller know that's how many we needed
        :param unpacked_data: a python list of the unpacked elements
        :return: value, number of items used from list
        '''

        if isinstance((self.data_type), StructObject):
            item_count = 0
            value_list = []
            for i in range(self.length):
                new_value, new_count = self.data_type.parse_unpacked(unpacked_data[item_count:])
                item_count += new_count
                value_list.append(new_value)
            return value_list, item_count

        else:
            value_list = unpacked_data[:self.length]
            return list(value_list), self.length

    def create_packlist(self, value):
        '''
        :return:
         returns a list that gets combined onto the end of the current list to be packed.
         It should match the format returned by get_format
         In this case value should be a listlike object
        '''
        if isinstance((self.data_type), StructObject):
            packlist = []
            for i in range(self.length):
                new_list = self.data_type.create_packlist(value[i])
                packlist += new_list
            return packlist
        else:
            return list(value)


class BinaryStructure(StructObject):
    '''
    This is the core binary struct class that will need used.
    '''
    def __init__(self, structure_dict, endianness):
        '''
        Initialize this class with a structure ordereddict (see example in the tests) to get an object
        you can use to convert back and forth from binary data and dicts
        :param structure_dict: ordereddict of the ALLCAPS types.  Can be nested to create complex structs
        :param endianness: one of the struct module's endian strings
        '''
        self.structure_dict = structure_dict
        self.endianness = endianness
        self.has_format = False
        self.format = self.get_format()
        self.has_format = True
        self.struct = struct.Struct(self.endianness + self.format)
        self.keys = list(self.structure_dict.keys())

    def get_format(self):
        parse_string = ''

        for k, v in self.structure_dict.items():
            if isinstance(v, OrderedDict):
                # create a new binary structure without an endianness
                new_binarystructure = BinaryStructure(v, '')
                self.structure_dict[k] = new_binarystructure
                v = new_binarystructure

            if isinstance(v, StructObject):
                parse_string += v.get_format()
            else:
                parse_string += v

        return parse_string

    def pack(self, data_dict):
        """
        Takes a dictionary (dict_input)
        and a OrderedDict as described at the top of the file
        and an opitonal offset and then return a regular (non-Ordered) dictionary
        with the data assigned to the keys.
        """
        data_list = self.create_packlist(data_dict)
        return self.struct.pack(*data_list)

    def create_packlist(self, value):
        '''
         returns a list that gets combined onto the end of the current list to be packed.
         It should match the format returned by get_format
        :return:
        '''
        data_list = []

        for k in self.keys:
            struct_type = self.structure_dict[k]
            val = value.get(k) # will return None if the key is missing
            if isinstance(struct_type, StructObject):
                data_list += struct_type.create_packlist(val)
            else:
                data_list.append(val)

        return data_list


    def unpack(self, data_array, offset=0):
        """
        Take raw response data which should be an iterable byte structure,
        and then return an ordered dictionary with the data assigned to the keys.
        """
        unpacked = self.struct.unpack_from(data_array, offset)

        return self.parse_unpacked(unpacked)[0]

    def parse_unpacked(self, unpacked_data):
        #final_dict = OrderedDict()
        final_dict = {}

        unpack_offset = 0
        for x in range(len(self.keys)):
            key = self.keys[x]
            format_type = self.structure_dict[key]
            if isinstance(format_type, StructObject):
                final_dict[key], new_offset = format_type.parse_unpacked(unpacked_data[x + unpack_offset:])
                unpack_offset += new_offset - 1
            else:
                final_dict[key] = unpacked_data[x + unpack_offset]

        return final_dict, len(self.keys) + unpack_offset


    def __len__(self):
        return self.struct.size



def run_tests():
    test2()
    test1()

def test2():
    original_input = b'\xFF' + b'\x01\x02\x03\x04\x00\x05\x06\x07\x08\x09' * 2 + b'\xEE'
    test_dict = OrderedDict()
    test_dict['one'] = UINT8
    test_dict['two'] = UINT8
    test_dict['nested'] = OrderedDict()
    test_dict['nested']['three'] = UINT8
    test_dict['nested']['four'] = UINT8
    test_dict['nested']['pad1'] = SPARE(1)
    test_dict['nested']['five'] = UINT8
    test_dict['six'] = UINT8
    test_dict['array'] = ARRAY(UINT8, 3)
    test_structure = BinaryStructure(test_dict, '<')

    test_dict2 = OrderedDict()
    test_dict2['starting_FF'] = UINT8
    test_dict2['two_substructs'] = ARRAY(test_structure, 2)
    test_dict2['ending_EE'] = UINT8

    test_structure2 = BinaryStructure(test_dict2, '<')
    result = test_structure2.unpack(original_input)

    expected_subdict = {'one': 1,
                        'two': 2,
                        'nested': {'three':3,
                                   'four': 4,
                                   'pad1': None,
                                   'five': 5},
                        'six': 6,
                        'array':[7,8,9]}
    expected_dict = {'starting_FF': 0xFF,
                     'two_substructs':  [expected_subdict, expected_subdict],
                     'ending_EE': 0xEE}
    assert(expected_dict == result)
    print('Complex Nest Unpack Pass')

    #Now lets go the other way
    result2 = test_structure2.pack(expected_dict)
    assert(result2 == original_input)
    print('Complex Nest Pack Pass')

    expected_subdict2 = {'one': 1,
                        'two': 2,
                        'nested': {'three':3,
                                   'four': 4,
                                   'five': 5},
                        'six': 6,
                        'array':[7,8,9]}
    expected_dict2 = {'starting_FF': 0xFF,
                     'two_substructs':  [expected_subdict2, expected_subdict2],
                     'ending_EE': 0xEE}


    result3 = test_structure2.pack(expected_dict2)
    assert (result3 == original_input)
    print('Complex Nest Pack Pass Without Padding')


def test1():
    original_input = b'\x01\x02\x03\x04\x00\x05\x06\x07\x08\x09'
    test_dict = OrderedDict()
    test_dict['one'] = UINT8
    test_dict['two'] = UINT8
    test_dict['nested'] = OrderedDict()
    test_dict['nested']['three'] = UINT8
    test_dict['nested']['four'] = UINT8
    test_dict['nested']['pad1'] = SPARE(1)
    test_dict['nested']['five'] = UINT8
    test_dict['six'] = UINT8
    test_dict['array'] = ARRAY(UINT8, 3)
    test_structure = BinaryStructure(test_dict, '<')

    #unpack the data and we'll compare it against what we should have gotten
    result = test_structure.unpack(original_input)
    #for completeness, we compare expect the dict that returns to have a pad1 value of None.
    expected_dict = {'one': 1,
                     'two': 2,
                     'nested': {'three':3,
                                'four': 4,
                                'pad1': None,
                                'five': 5},
                     'six': 6,
                     'array':[7,8,9]}

    assert(expected_dict == result)
    print('test unpack OK')


    #Now we re-build the original data bytes from what we expected and should get what we started with.
    result2 = test_structure.pack(expected_dict)
    assert(original_input == result2)
    print('test pack OK')

    #because the padding is optional, we shouldn't need to supply it when packing the data
    expected_dict_nopad = {'one': 1,
                           'two': 2,
                           'nested': {'three': 3,
                                      'four': 4,
                                      'five': 5},
                           'six': 6,
                           'array': (7, 8, 9)}

    result3 = test_structure.pack(expected_dict_nopad)
    assert(original_input == result3)
    print('test pack without pad OK')


if __name__ == '__main__':
  run_tests()
