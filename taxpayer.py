from dataclasses import asdict, dataclass

from lxml import etree


@dataclass
class Taxpayer:
    taxNumber: str
    name: str
    address: str
    city: str
    postNumber: str
    postName: str
    email: str
    phone: str
    birthDate: str

    def __init__(self, args):
        self.path = args.taxpayer or "cache/taxpayer.xml"
        try:
            tree = etree.parse(self.path)  # type: ignore
            root = tree.getroot()
            for key in asdict(self).keys():
                try:
                    setattr(self, key, root.findtext(key))
                except AttributeError:
                    value = input(f"Enter your {key}: ")
                    setattr(self, key, value)
        except OSError:
            for key in asdict(self).keys():
                value = input(f"Enter your {key}: ")
                setattr(self, key, value)

    def save(self):
        with etree.xmlfile(self.path, encoding="utf-8") as xf:
            xf.write_declaration()
            root = etree.Element("taxpayer")
            for key, value in asdict(self).items():
                el = etree.SubElement(root, key)
                el.text = value
            xf.write(root, pretty_print=True)
