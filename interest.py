from dataclasses import dataclass
from enum import Enum
from typing import Literal, Optional

from lxml.builder import ElementMaker
from lxml.etree import ElementBase

from taxpayer import Taxpayer


class InterestType(Enum):
    FUND_INTEREST = 7
    NON_EU_BANK_INTEREST = 3


@dataclass
class Interest:
    # Date of the interest payment
    date: str
    # Identification number of the payer if legal person
    identification_number: str
    # Name of the payer
    name: str
    # Address of the payer
    address: str
    # Country of the payer
    country: str
    # Type of interest
    type: InterestType
    # Value of the interest
    value: float
    # Country of the source
    country2: str
    # Foreign tax
    foreign_tax: Optional[float] = None
    # Relief statement
    relief_statement: Optional[str] = None


@dataclass
class DohObr:
    self_report: bool
    wf_type_u: bool
    # Year of the interest report
    period: int
    # Document workflow ID
    document_workflow_id: Literal["O"]
    # Email of the taxpayer
    email: str
    # Telephone number of the taxpayer
    telephone_number: str
    # Whether the taxpayer is a resident of Slovenia
    resident_of_slovenia: bool
    # Country of the taxpayer
    country: Literal["SI"]
    # Interests
    interests: list[Interest]

    def __init__(self, period: int, taxpayer: Taxpayer) -> None:
        self.self_report = False
        self.wf_type_u = False
        self.period = period
        self.document_workflow_id = "O"
        self.email = taxpayer.email
        self.telephone_number = taxpayer.phone
        self.resident_of_slovenia = True
        self.country = "SI"
        self.interests = []
        self.taxpayer = taxpayer

    def add_interest(self, interest: Interest):
        self.interests.append(interest)

    def to_xml(self) -> ElementBase:
        # Define namespaces
        EDP_NS = "http://edavki.durs.si/Documents/Schemas/EDP-Common-1.xsd"
        DOH_OBR_NS = "http://edavki.durs.si/Documents/Schemas/Doh_Obr_2.xsd"

        # Create ElementMakers for each namespace
        E = ElementMaker(nsmap={"edp": EDP_NS})
        EDP = ElementMaker(namespace=EDP_NS)

        # Create the envelope structure
        envelope = E.Envelope(
            {"xmlns": DOH_OBR_NS},
            # Header section with taxpayer info
            EDP.Header(
                EDP.taxpayer(
                    EDP.taxNumber(self.taxpayer.taxNumber),
                    EDP.taxpayerType("FO"),
                    EDP.name(self.taxpayer.name),
                    EDP.address1(self.taxpayer.address),
                    EDP.city(self.taxpayer.city),
                    EDP.postNumber(self.taxpayer.postNumber),
                    EDP.postName(self.taxpayer.postName),
                ),
            ),
            EDP.AttachmentList(),
            EDP.Signatures(),
            E.body(
                EDP.bodyContent(),
                E.Doh_Obr(
                    E.SelfReport(str(self.self_report).lower()),
                    E.WfTypeU(str(self.wf_type_u).lower()),
                    E.Period(str(self.period)),
                    E.DocumentWorkflowID(self.document_workflow_id),
                    E.Email(self.email),
                    E.TelephoneNumber(self.telephone_number),
                    E.ResidentOfRepublicOfSlovenia(
                        str(self.resident_of_slovenia).lower()
                    ),
                    E.Country(self.country),
                    *[
                        E.Interest(
                            E.Date(interest.date),
                            E.IdentificationNumber(interest.identification_number),
                            E.Name(interest.name),
                            E.Address(interest.address),
                            E.Country(interest.country),
                            E.Type(str(interest.type.value)),
                            E.Value("{:.2f}".format(interest.value)),
                            *(
                                [E.ForeignTax("{:.2f}".format(interest.foreign_tax))]
                                if interest.foreign_tax
                                else []
                            ),
                            E.Country2(interest.country2),
                            *(
                                [E.ReliefStatement(interest.relief_statement)]
                                if interest.relief_statement
                                else []
                            ),
                        )
                        for interest in self.interests
                    ],
                ),
            ),
        )

        return envelope

    def condense_interests(self):
        """
        Condenses multiple interest entries from the same payer into a single entry.
        The new entry will:
        - Use the earliest date
        - Sum all values
        - Keep the same payer information
        """
        condensed = {}

        for interest in self.interests:
            key = (
                interest.identification_number,
                interest.name,
                interest.address,
                interest.country,
                interest.type,
                interest.country2,
            )

            if key in condensed:
                # Update existing entry
                existing = condensed[key]
                # Keep the later date
                if interest.date > existing.date:
                    existing.date = interest.date
                # Add the values (round to avoid float precision issues)
                existing.value = round(existing.value + interest.value, 4)
            else:
                # Create new entry
                condensed[key] = Interest(
                    interest.date,
                    interest.identification_number,
                    interest.name,
                    interest.address,
                    interest.country,
                    interest.type,
                    interest.value,
                    interest.country2,
                )

        # Replace the interests list with condensed version
        self.interests = list(condensed.values())
