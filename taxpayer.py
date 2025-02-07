import datetime
from dataclasses import asdict, dataclass, fields

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
            for field in fields(self):
                try:
                    setattr(self, field.name, root.findtext(field.name))
                except AttributeError:
                    value = input(f"Enter your {field.name}: ")
                    setattr(self, field.name, value)
        except OSError:
            for field in fields(self):
                value = input(f"Enter your {field.name}: ")
                setattr(self, field.name, value)

    def save(self):
        with etree.xmlfile(self.path, encoding="utf-8") as xf:
            xf.write_declaration()
            root = etree.Element("taxpayer")
            for key, value in asdict(self).items():
                el = etree.SubElement(root, key)
                el.text = value
            xf.write(root, pretty_print=True)

    def get_birth_date(self) -> datetime.date:
        return datetime.datetime.strptime(self.birthDate, "%d.%m.%Y").date()
