import pandas as pd
from lxml import etree
from lxml.builder import ElementMaker


class XML:
    MAIN_NS = "http://edavki.durs.si/Documents/Schemas/Doh_Div_3.xsd"
    EDP_NS = "http://edavki.durs.si/Documents/Schemas/EDP-Common-1.xsd"

    def __init__(self, taxpayer, df: pd.DataFrame, path: str, correction: bool) -> None:
        self.taxpayer = taxpayer
        self.df = df
        self.xml = XMLWriter(path)
        self.correction = correction

    def write(self):
        E = ElementMaker(nsmap={"edp": self.EDP_NS})
        EDP = ElementMaker(namespace=self.EDP_NS)
        envelope = E.Envelope(
            {"xmlns": self.MAIN_NS},
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
                EDP.Workflow(
                    EDP.DocumentWorkflowID("P" if self.correction else "O"),
                    EDP.DocumentWorkflowName(),
                ),
                EDP.domain("edavki.durs.si"),
            ),
            EDP.AttachmentList(),
            EDP.Signatures(),
            E.body(
                E.Doh_Div(
                    E.Period(str(pd.Timestamp.now().year - 1)),
                    E.EmailAddress(self.taxpayer.email),
                    E.PhoneNumber(self.taxpayer.phone),
                    E.ResidentCountry("SI"),
                    E.IsResident("true"),
                    E.SelfReport("false"),
                    E.WfTypeU("false"),
                ),
                *[
                    E.Dividend(
                        E.Date(row.Date.strftime("%Y-%m-%d")),  # type: ignore
                        E.PayerIdentificationNumber(row.PayerIdentificationNumber),
                        E.PayerName(row.PayerName),
                        E.PayerAddress(row.PayerAddress),
                        E.PayerCountry(row.PayerCountry),
                        E.Type("1"),
                        E.Value("{:.2f}".format(row.Value)),
                        E.ForeignTax("{:.2f}".format(row.ForeignTax)),
                        E.SourceCountry(row.PayerCountry),
                        E.ReliefStatement(row.ReliefStatement),
                    )
                    for row in self.df.itertuples()
                ],
            ),
        )
        self.xml.write(envelope)

    def verify(self, schema_path: str):
        self.xml.verify(schema_path)


class XMLWriter:
    def __init__(self, path: str) -> None:
        self.path = path

    def write(self, element: etree.Element):  # type: ignore
        # Write the xml to a file pretty printed with an xml declaration
        with etree.xmlfile(self.path, encoding="utf-8") as xf:
            xf.write_declaration()
            xf.write(element, pretty_print=True)
            print("XML file written to ", self.path)

    def verify(self, schema_path: str):
        # Verify the generated XML using an xsd schema
        schema = etree.XMLSchema(etree.parse(schema_path))
        xml = etree.parse(self.path)
        schema.assertValid(xml)
        print("XML is valid according to schema ", schema_path)
