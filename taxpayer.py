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

    @classmethod
    def from_file(cls, taxpayer_file):
        taxpayer = etree.parse(taxpayer_file)
        return cls(
            taxpayer.findtext("taxNumber"),
            taxpayer.findtext("name"),
            taxpayer.findtext("address"),
            taxpayer.findtext("city"),
            taxpayer.findtext("postNumber"),
            taxpayer.findtext("postName"),
            taxpayer.findtext("email"),
            taxpayer.findtext("phone"),
        )

