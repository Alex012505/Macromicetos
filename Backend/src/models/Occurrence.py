import uuid
import datetime as dt
from sqlalchemy import Date, DateTime, ForeignKey, SmallInteger, Text, func
from sqlalchemy import Enum as SQLEnum
from sqlalchemy.orm import Mapped, mapped_column

from database.Base import Base
from models.Event import Event
from models.TaxonRef import TaxonRef
from models.UserWeb import PK

BASIS_OF_RECORD_ENUM = SQLEnum(
    'HumanObservation', 'PreservedSpecimen', 'MaterialSample', 'MachineObservation',
    'LivingSpecimen', 'FossilSpecimen', 'Occurrence',
    name="basis_of_record_enum", create_type=False,
)
OCCURRENCE_STATUS_ENUM = SQLEnum('present', 'absent', name="occurrence_status_enum", create_type=False)
ID_QUALIFIER_ENUM = SQLEnum('cf.', 'aff.', 'sp.', 'ssp.', 'none', name="id_qualifier_enum", create_type=False)
SUBSTRATE_ENUM = SQLEnum(
    'Soil', 'Humus', 'Grounds', 'Floor', 'FertilizedLand', 'Grasslands', 'Paddocks',
    'Litter', 'LeafLitter', 'Leaves', 'VegetableDebris', 'FernPetioles',
    'DeadWood', 'DecayingWood', 'VeryDecomposedFallenWood', 'HalfBuriedWood',
    'DeadWoodFromWoodyPlants', 'WoodRemains', 'Wood', 'Hardwood',
    'BurnedLog', 'FreshlyBurnedLogs', 'DecayingLogs', 'FallenLogs',
    'Logs', 'FallenOrStandingTrunks', 'LiveTreeTrunks', 'StumpAttachedToTheGround', 'Bunk',
    'Branches', 'LargeFallenDeadBranches', 'MediumFallenDeadBranches',
    'SmallFallenDeadBranches', 'LiveOrDeadBranchesOfDeciduousTrees', 'DecayingBranchesAndLeaves',
    'DecomposingBamboo', 'DecayingGuadua',
    'LivingWood', 'TreeParasite', 'CultivatedPlantMaterial', 'Roots', 'Stems',
    'PineCones', 'Dung', 'HorseManure', 'BeefManure',
    'AssociatedWithMoss', 'OtherDecayingAgaricals', 'Stubble', 'Debris', 'Other',
    name="substrate_enum", create_type=False,
)


class Occurrence(Base):
    """Un organismo observado (ecological.occurrence), tabla central de Capa 1."""
    __tablename__ = "occurrence"
    __table_args__ = {"schema": "ecological"}

    occurrence_id: Mapped[uuid.UUID] = mapped_column(PK(), primary_key=True, default=uuid.uuid4)
    event_id: Mapped[uuid.UUID] = mapped_column(
        PK(), ForeignKey(Event.event_id, onupdate="CASCADE", ondelete="RESTRICT"), nullable=False
    )
    taxon_id: Mapped[uuid.UUID | None] = mapped_column(
        PK(), ForeignKey(TaxonRef.taxon_id, onupdate="CASCADE", ondelete="SET NULL")
    )
    external_occurrence_id: Mapped[str | None] = mapped_column(Text, unique=True)
    basis_of_record: Mapped[str] = mapped_column(BASIS_OF_RECORD_ENUM, default="HumanObservation", nullable=False)
    recorded_by: Mapped[str | None] = mapped_column(Text)
    event_date: Mapped[dt.datetime | None] = mapped_column(DateTime(timezone=True))
    occurrence_status: Mapped[str] = mapped_column(OCCURRENCE_STATUS_ENUM, default="present", nullable=False)
    individual_count: Mapped[int | None] = mapped_column(SmallInteger)
    occurrence_remarks: Mapped[str | None] = mapped_column(Text)
    verbatim_scientific_name: Mapped[str | None] = mapped_column(Text)
    identification_qualifier: Mapped[str | None] = mapped_column(ID_QUALIFIER_ENUM, default="none")
    identified_by: Mapped[str | None] = mapped_column(Text)
    date_identified: Mapped[dt.date | None] = mapped_column(Date)
    substrate: Mapped[str | None] = mapped_column(SUBSTRATE_ENUM)
    associated_organisms: Mapped[str | None] = mapped_column(Text)
    associated_references: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[object] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[object] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())