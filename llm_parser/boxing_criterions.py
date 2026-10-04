import pymupdf
from typing import Annotated
from enum import Enum

from pydantic import BaseModel, Field, StringConstraints

Line = Annotated[str, StringConstraints(max_length=120)]


class ObjectType(Enum):
    Colonne = "colonne"
    Semelle = "semelle"
    Empattement = "empattement"
    Integrite = "intégrite"


class SeriesType(Enum):
    S100 = "S-100"
    S500 = "S-500"


class BoxingCriterion:
    def __init__(self, codes: list[str], schema: type[BaseModel], object_type: ObjectType, series_type: SeriesType):
        self.codes = codes
        self.schema = schema
        self.object_type = object_type
        self.series_type = series_type

    def __eq__(self, other):
        return self.__dict__ == other.__dict__

    def get_box(self, code: str, rect: pymupdf.Rect) -> pymupdf.Rect:
        pass


class Semelle(BaseModel):
    id: Line
    data: list[Line] = Field(max_length=16)


class SemelleBoxingCriterion(BoxingCriterion):
    def __init__(self):
        super().__init__(["SEMELLE,", "COUPE"], Semelle, ObjectType.Semelle, SeriesType.S100)

    def get_box(self, code: str, rect: pymupdf.Rect) -> pymupdf.Rect:
        if code in self.codes:
            x0 = rect.x0
            y0 = rect.y0
            x1 = rect.x0 + min(rect.width * 5, 400)
            y1 = rect.y1 + min(rect.height * 6, 400)
            return pymupdf.Rect(x0, y0, x1, y1)


class Empattement(BaseModel):
    id: Line
    data: list[Line] = Field(max_length=16)


class EmpattementBoxingCriterion(BoxingCriterion):
    def __init__(self):
        super().__init__(["EMPATTEMENT"], Empattement, ObjectType.Empattement, SeriesType.S100)

    def get_box(self, code: str, rect: pymupdf.Rect) -> pymupdf.Rect:
        if code == self.codes[0]:
            x0 = rect.x0
            y0 = rect.y0
            x1 = rect.x0 + min(rect.width * 2, 200)
            y1 = rect.y1 + min(rect.height * 5, 300)
            return pymupdf.Rect(x0, y0, x1, y1)


class Colonne(BaseModel):
    id: Line
    data: list[Line] = Field(max_length=16)


class ColonneBoxingCriterion(BoxingCriterion):
    def __init__(self):
        super().__init__(["COL :", "COL:"], Colonne, ObjectType.Colonne, SeriesType.S500)

    def get_box(self, code: str, rect: pymupdf.Rect) -> pymupdf.Rect:
        if code in self.codes:
            x0 = rect.x0
            y0 = rect.y0
            x1 = rect.x0 + min(rect.width * 6, 400)
            y1 = rect.y1 + min(rect.height * 3, 300)
            return pymupdf.Rect(x0, y0, x1, y1)


class Integrite(BaseModel):
    id: Line
    data: list[Line] = Field(max_length=16)


class IntegriteBoxingCriterion(BoxingCriterion):
    def __init__(self):
        super().__init__(["INTÉGRITÉ,", "INTÉGRITÉ ,", "INTEGRITE,", "INTEGRITE ,"], Integrite, ObjectType.Integrite, SeriesType.S500)

    def get_box(self, code: str, rect: pymupdf.Rect) -> pymupdf.Rect:
        if code in self.codes:
            x0 = rect.x0
            y0 = rect.y0
            x1 = rect.x0 + min(rect.width * 6, 400)
            y1 = rect.y1 + min(rect.height * 3, 300)
            return pymupdf.Rect(x0, y0, x1, y1)


CRITERIONS = [
    SemelleBoxingCriterion(),
    EmpattementBoxingCriterion(),
    ColonneBoxingCriterion(),
    IntegriteBoxingCriterion(),
]