"""
Tool for converting simple 'C' struct and #define lists into Python classes.

The subset of C that is understand is limited to:

    #define <group>_<name> <value>

    struct X
    {
        <type> <name>;
        <type> <name>[dimension];
    };

Blank lines and single-line comments are ignored.

defines are expected to be in contiguous groups with a pattern of naming that
has each define start with a grouping, e.g.

    #define GL_FOG_DENSITY 0x01
    #define GL_FOG_START   0x02
    #define GL_FOG_END     0x03

    #define GL_SAMPLE_ALPHA ...

Optionally, you can specify a prefix that is taken and turned into a title.

Given a prefix of 'GL_', the above would create

    class Gl_Fog:
        DENSITY = 0x01
        START   = 0x02
        END     = 0x03

    class Gl_SAMPLE:
        ALPHA   = ...

structs are converted into PackedStruct objects, which can then be accessed
by taking the field name, prefixing it with 'm' and using it as an attribute

    struct myHeader
    {
        char    name[8];
        int     value;
    };

if parsed with a prefix of 'my' would produce 'class MyHeader' with members
'mName' and 'mValue'.

You can then use these to consume data from a stream by using

    fh = open('file_with_my_header', 'rb')
    struct = MyHeader(fh)
    print(struct.mName, struct.mValue)
"""

from struct import calcsize, pack, unpack
import logging
import re

""" Map C types to the 'struct' representations. """
TYPE_MAP = {
    'char': 's',
    'int': 'i',
    'short': 'h',
    'float': 'f',
    'double': 'd',
    'uint16': 'H',
    'uint32': 'I',
    'sint16': 'h',
    'sint32': 'i',
    'uint16_t': 'H',
    'uint32_t': 'I',
    'sint16_t': 'h',
    'sint32_t': 'i',
}

""" Pattern for removing single-line comments. """
CMT_REMOVE = re.compile('\s*//.*').sub

""" For matching the array dimensions of a field. """
ARRAY_MATCH = re.compile(r'(\S+)\[(\d+)\]').match

""" Format the definition of a struct. """
STRUCT_FMT = (
    "{struct} = PackedStruct.create("
    "'{struct}',"
    " {fields},"
    " net_endian={end}"
    ")\n"
    "\n"
)


class PackedStruct(object):
    """
    BaseClass for implementing pack/unpack struct representations, created
    by calling `PackedStruct.create().

    See the `Converter` class for generating this automatically from C/C++
    structure definitions.
    """

    def __init__(self, fh):
        self._values = unpack(self.STRUCT, fh.read(self.SIZE))

    def __getitem__(self, key):
        return self._values[self.FIELDS[key]]

    @staticmethod
    def create(struct_name, fields, net_endian=False):
        """
        Create a PackedStruct class describing the representation of a binary
        data structure as might be specified via a C 'struct'.

        The field list is an iterable of (defn, fieldname), where defn is the
        `struct` field representation.

        Fields can be accessed as attributes by using the name prefixed with
        'm' and parsed as title(), e.g. "('2h', 'shorts')" would be mShorts.

        :param struct_name: The name of the struct and class.
        :param fields: An iterable of field descriptions where each entry is
                       a tuple of (`struct` representation, fieldname)
        :param net_endian: True or False whether the data is stored in
                       network endian order.
        :return:       A class definition.
        """

        struct_defs, members = [], {}

        # build a list of lambdas to implement the members.
        for defn, field_name in fields:
            field_name = "m" + field_name.title()
            member_num = len(members)
            members[field_name] = property(
                lambda self, n=member_num: self._values[int(n)]
            )
            struct_defs.append(defn)

        struct_def = "".join(struct_defs)
        if net_endian: struct_def = '!' + struct_def

        cls_members = {
            'STRUCT': struct_def,
            'SIZE': calcsize(struct_def),
        }
        cls_members.update(members)

        return type(struct_name, (PackedStruct,), cls_members)


class Converter(object):
    """ Helper for parsing .h file-like definitions to generate PackedStructs. """

    def __init__(self, indent="    ", logger=None):

        self.indent = indent
        self.logger = logger or logging
        self.types = set()

        self._define_group = None
        self._struct_name = None


    def _read_define(self, line, prefix):
        """
        Internal: Read a #define definition line.
        :param line: the line to process
        :param prefix: prefix being used
        :return: text to add to the current definition.
        """

        # #define <name> <value>
        _, name, value = line.split()

        # If there's a prefix, strip it.
        if prefix:
            assert name.startswith(prefix)
            name = name[len(prefix):]

        text = ""
        # take the value up to the first _ as the grouping,
        # everything after it is the name.
        grouping, name = name.split('_', 1)
        if grouping != self._define_group:
            if self._define_group:
                text += "\n"
            self._define_group = grouping
            self._struct_name = None

            typename = prefix.title() + grouping.upper()
            if typename in self.types:
                raise ValueError("Duplicate type: %s" % typename)
            self.logger.info("enum %s", typename)
            self.types.add(typename)

            text += "class %s:\n" % typename
            text += self.indent + "# Enums\n"

        self.logger.debug("enum %s.%s = %s", self._define_group,
                          name, value)
        return text + self.indent + "%s = %s\n" % (name, value)


    def parse(self, iterable, prefix="", net_endian=False):
        """
        Process c-like #defines, structs and members from an iterable of lines
        of text, generating text to produce equivalent PackedStruct classes
        in Python.

        :param iterable: iterable of lines to parse
        :param prefix: [optional] prefix to require infront of structs/defines.
        :param net_endian: Set to True for the '!' prefix on struct definitions.
        :return: Python text string that would generate the supplied structures.
        """

        logger = self.logger
        struct_fields, text = None, ""

        for line in iterable:

            # Get rid of cruft.
            line = CMT_REMOVE('', line.rstrip().replace(';', ''))
            line = line.replace('\t', ' ')
            if not line: continue

            # '#define' statements get converted into blocks.
            if line.startswith('#define'):
                text += self.read_define(line, prefix)
                continue

            # nop the open brace of a structure definition.
            if line.startswith('{'):
                assert self._struct_name
                assert struct_fields is None
                struct_fields = []
                continue

            # end of a struct
            if line.startswith('}'):
                assert self._struct_name
                text += STRUCT_FMT.format(struct=self._struct_name,
                                          fields=tuple(struct_fields), end=net_endian)
                self._struct_name, fields = None, None
                continue

            # The remaining lines we understand are 'struct X' and 'type Name'.
            try:
                typename, field = line.split()
            except Exception as e:
                # Anything else we just ignore.
                logger.debug("Ignoring %s: %s", line, str(e))
                continue

            # struct definition.
            if typename == 'struct':
                if self._define_group:
                    # So we get a blank link between enums and structs.
                    self._define_group = None
                    text += "\n"

                # Turn the field name into something we can use
                if prefix:
                    assert field.startswith(prefix)
                    field = prefix.title() + field[len(prefix):].title()
                else:
                    field = field.title()

                if field in self.types:
                    raise ValueError("Duplicate type: %s", field)
                logger.info('struct %s', field)

                # Add to the types list
                self._struct_name = field
                self.types.add(field)
                struct_fields = None
                continue

            # Otherwise it's a member declaration (we think).

            # If it's an array, prefix the type by the count
            m = ARRAY_MATCH(field)
            if m:
                field, count = m.group(1), str(m.group(2))
            else:
                count = ''

            # Put the count and type together for the representation, e.g.
            # a single int => 'i', 8 shorts => '8h', etc.
            type_rep = str(count) + TYPE_MAP[typename]

            logger.debug('%s.%s %s', self._struct_name, type_rep, field)
            struct_fields.append((type_rep, field))

        return text

