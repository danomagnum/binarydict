# binarydict

A high level struct module for python that makes the default struct module human readable.  
The main use case I've found for this is pulling data out of binary files and raw tcp streams that are sending structs from the native language.

The basic idea is to create an OrderedDict for each struct.  You can nest them as desired.  This allows a fairly readable way to define structures.

Example
```
from binary_dict import CHAR, SINT8, UINT8, BOOL, SINT16, UINT16, SINT32, UINT32,\
                        SINT64, UINT64, SINT_NATIVE, UINT_NATIVE, HALF, FLOAT, DOUBLE, \
                        STRING, SPARE, ARRAY, BinaryStructure
from collections import OrderedDict

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
test_structure = BinaryStructure(test_dict)

# this is a binary stream that goes from 1-9
binary_input = b'\x01\x02\x03\x04\x00\x05\x06\x07\x08\x09'

result = test_structure.unpack(binary_input)

#result is a dict as shown below
#result = {'one': 1,
#          'two': 2,
#          'nested': {'three':3,
#                     'four': 4,
#                     'pad1': None,
#                     'five': 5},
#          'six': 6,
#          'array':[7,8,9]}

```

You can also nest structures themselves.

```
#continuing using test_structure from the last example.
# this structure consists of the byte 0xFF, two of the test_structures, and then the byte 0xEE.
test_dict2 = OrderedDict()
test_dict2['starting_FF'] = UINT8
test_dict2['two_substructs'] = ARRAY(test_structure, 2)
test_dict2['ending_EE'] = UINT8

test_structure2 = BinaryStructure(test_dict2)


expected_subdict = {'one': 1,
                    'two': 2,
                     'nested': {'three':3,
                                'four': 4,
                                'pad1': None,
                                'five': 5},
                     'six': 6,
                     'array':[7,8,9]}

#for the example we'll use two of the exact same substructs.  They could be differen though of course.
binary_input = b'\xFF' + b'\x01\x02\x03\x04\x00\x05\x06\x07\x08\x09' * 2 + b'\xEE'

expected_dict = {'starting_FF': 0xFF,
                 'two_substructs':  [expected_subdict, expected_subdict],
                 'ending_EE': 0xEE}
 
result = test_structure2.unpack(original_input)

#result should now match expected_dict



```
