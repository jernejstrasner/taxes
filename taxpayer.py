import dataclasses
from lxml import etree


@dataclasses.dataclass
class Taxpayer:
    taxNumber: str
    name: str
    address: str
    city: str
    postNumber: str
    postName: str
    email: str
    phone: str

    def __init__(self):
        self.path = "data/taxpayer.xml"
        try:
            tree = etree.parse(self.path)
            root = tree.getroot()
            self.taxNumber = root.findtext("taxNumber")
            self.name = root.findtext("name")
            self.address = root.findtext("address")
            self.city = root.findtext("city")
            self.postNumber = root.findtext("postNumber")
            self.postName = root.findtext("postName")
            self.email = root.findtext("email")
            self.phone = root.findtext("phone")
        except (OSError, AttributeError):
            self.taxNumber = None
            self.name = None
            self.address = None
            self.city = None
            self.postNumber = None
            self.postName = None
            self.email = None
            self.phone = None
            self.get_input()

    def save(self):
        with etree.xmlfile(self.path, encoding="utf-8") as xf:
            xf.write_declaration()
            root = etree.Element("taxpayer")
            for key, value in dataclasses.asdict(self).items():
                el = etree.SubElement(root, key)
                el.text = value
            xf.write(root, pretty_print=True)

    def get_input(self):
        if not self.taxNumber:
            self.taxNumber = input("Enter your tax number: ")
        else:
            verification = input(f"Is your tax number {self.taxNumber}? (Y/N): ")
            if verification.upper() != "Y":
                self.taxNumber = input("Enter your tax number: ")

        if not self.name:
            self.name = input("Enter your name: ")
        else:
            verification = input(f"Is your name {self.name}? (Y/N): ")
            if verification.upper() != "Y":
                self.name = input("Enter your name: ")

        if not self.address:
            self.address = input("Enter your address: ")
        else:
            verification = input(f"Is your address {self.address}? (Y/N): ")
            if verification.upper() != "Y":
                self.address = input("Enter your address: ")

        if not self.city:
            self.city = input("Enter your city: ")
        else:
            verification = input(f"Is your city {self.city}? (Y/N): ")
            if verification.upper() != "Y":
                self.city = input("Enter your city: ")

        if not self.postNumber:
            self.postNumber = input("Enter your post number: ")
        else:
            verification = input(f"Is your post number {self.postNumber}? (Y/N): ")
            if verification.upper() != "Y":
                self.postNumber = input("Enter your post number: ")

        if not self.postName:
            self.postName = input("Enter your post name: ")
        else:
            verification = input(f"Is your post name {self.postName}? (Y/N): ")
            if verification.upper() != "Y":
                self.postName = input("Enter your post name: ")

        if not self.email:
            self.email = input("Enter your email: ")
        else:
            verification = input(f"Is your email {self.email}? (Y/N): ")
            if verification.upper() != "Y":
                self.email = input("Enter your email: ")

        if not self.phone:
            self.phone = input("Enter your phone: ")
        else:
            verification = input(f"Is your phone {self.phone}? (Y/N): ")
            if verification.upper() != "Y":
                self.phone = input("Enter your phone: ")
        
        self.save()
