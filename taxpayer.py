from dataclasses import asdict, dataclass
from typing import Optional

from lxml import etree


@dataclass
class Taxpayer:
    taxNumber: Optional[str] = None
    name: Optional[str] = None
    address: Optional[str] = None
    city: Optional[str] = None
    postNumber: Optional[str] = None
    postName: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    birthDate: Optional[str] = None

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
