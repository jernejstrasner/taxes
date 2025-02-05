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
            self.taxNumber = root.findtext("taxNumber")
            self.name = root.findtext("name")
            self.address = root.findtext("address")
            self.city = root.findtext("city")
            self.postNumber = root.findtext("postNumber")
            self.postName = root.findtext("postName")
            self.email = root.findtext("email")
            self.phone = root.findtext("phone")
            self.birthDate = root.findtext("birthDate")
        except (OSError, AttributeError):
            self.get_input()

    def save(self):
        with etree.xmlfile(self.path, encoding="utf-8") as xf:
            xf.write_declaration()
            root = etree.Element("taxpayer")
            for key, value in asdict(self).items():
                el = etree.SubElement(root, key)
                el.text = value
            xf.write(root, pretty_print=True)

    def get_input(self):
        # If we have all the data, we can ask the user to verify it at once
        if all(
            [
                self.taxNumber,
                self.name,
                self.address,
                self.city,
                self.postNumber,
                self.postName,
                self.email,
                self.phone,
                self.birthDate,
            ]
        ):
            verification = input(
                f"Is this information correct?\nTax number: {self.taxNumber}\nName: {self.name}\nAddress: {self.address}\nCity: {self.city}\nPost number: {self.postNumber}\nPost name: {self.postName}\nEmail: {self.email}\nPhone: {self.phone}\nBirth date: {self.birthDate}\n(Y/N): "
            )
            if verification.upper() != "Y" and verification != "":
                self.taxNumber = input("Enter your tax number: ")
                self.name = input("Enter your name: ")
                self.address = input("Enter your address: ")
                self.city = input("Enter your city: ")
                self.postNumber = input("Enter your post number: ")
                self.postName = input("Enter your post name: ")
                self.email = input("Enter your email: ")
                self.phone = input("Enter your phone: ")
                self.birthDate = input("Enter your birth date: ")
            self.save()
            return

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

        if not self.birthDate:
            self.birthDate = input("Enter your birth date: ")
        else:
            verification = input(f"Is your birth date {self.birthDate}? (Y/N): ")
            if verification.upper() != "Y":
                self.birthDate = input("Enter your birth date: ")

        self.save()
