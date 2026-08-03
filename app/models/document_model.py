class DocumentModel:
    def __init__(self, name="", id_number="", document_type="unknown"):
        self.name = name
        self.id_number = id_number
        self.document_type = document_type

    def to_dict(self):
        return {
            "name": self.name,
            "id_number": self.id_number,
            "document_type": self.document_type,
        }
