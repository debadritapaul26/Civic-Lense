"""Seed realistic multilingual demo data for the civic AI platform.

Run from the project root with:

    python seed_data/seed.py
"""

from __future__ import annotations

import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Optional


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.database import SessionLocal, engine
from backend.models.db_models import Base, Complaint, District, Proposal
from backend.services.location_cluster_service import get_all_location_clusters


@dataclass(frozen=True)
class DistrictSeed:
    """Values used to create one district."""

    name: str
    population: int
    income_level: str
    existing_infra_score: float


@dataclass(frozen=True)
class ComplaintSeed:
    """Values used to create one complaint."""

    district_name: str
    raw_text: str
    language_detected: str
    category: str
    urgency_score: float
    evidence_file_path: Optional[str] = None


DISTRICT_COORDINATES: dict[str, tuple[float, float]] = {
    "District A": (22.5726, 88.3639),
    "District B": (19.0760, 72.8777),
    "District C": (13.0827, 80.2707),
}


@dataclass(frozen=True)
class ProposalSeed:
    """Values used to create one funding proposal."""

    district_name: str
    project_name: str
    requested_amount: float


DISTRICTS: tuple[DistrictSeed, ...] = (
    DistrictSeed("District A", 500_000, "high", 7.5),
    DistrictSeed("District B", 350_000, "medium", 5.0),
    DistrictSeed("District C", 200_000, "low", 2.5),
)


COMPLAINTS: tuple[ComplaintSeed, ...] = (
    ComplaintSeed(
        "District A",
        "Amar para-r road ta bhison kharap, please repair korun.",
        "Bengali+English",
        "Road",
        6.0,
        "uploads/sample_pothole_1.jpg",
    ),
    ComplaintSeed(
        "District A",
        "Hamare gali mein teen din se paani nahi aa raha, please check kijiye.",
        "Hindi+English",
        "Water",
        5.0,
    ),
    ComplaintSeed(
        "District A",
        "Clinic-e doctor nei, appointment er jonno onek wait korte hocche.",
        "Bengali+English",
        "Healthcare",
        7.0,
    ),
    ComplaintSeed(
        "District A",
        "Transformer baar baar trip aaguthu, current is gone every night.",
        "Tamil+English",
        "Electricity",
        6.0,
        "uploads/sample_transformer_1.jpg",
    ),
    ComplaintSeed(
        "District A",
        "Main road-er streetlights kaaj korche na, very unsafe after dark.",
        "Bengali+English",
        "Road",
        8.0,
    ),
    ComplaintSeed(
        "District A",
        "Enga area-la drinking water pressure romba low, please inspect pannunga.",
        "Tamil+English",
        "Water",
        4.0,
    ),
    ComplaintSeed(
        "District A",
        "Sarkari hospital mein medicines available nahi hain, help needed.",
        "Hindi+English",
        "Healthcare",
        5.0,
    ),
    ComplaintSeed(
        "District A",
        "Load shedding abar hocche, students cannot study at night.",
        "Bengali+English",
        "Electricity",
        7.0,
        "uploads/sample_outage_1.mp4",
    ),
    ComplaintSeed(
        "District B",
        "Hamare ward ka pothole bahut bada ho gaya hai, bikes are falling.",
        "Hindi+English",
        "Road",
        7.0,
        "uploads/sample_pothole_2.jpg",
    ),
    ComplaintSeed(
        "District B",
        "Brishti hole pura para jol-e dubey jay, drainage please fix korun.",
        "Bengali+English",
        "Water",
        8.0,
        "uploads/sample_flooding_1.mp4",
    ),
    ComplaintSeed(
        "District B",
        "Government hospital-la nurse shortage irukku, waiting time too long.",
        "Tamil+English",
        "Healthcare",
        6.0,
    ),
    ComplaintSeed(
        "District B",
        "Bijli roz shaam ko chali jaati hai, small businesses are suffering.",
        "Hindi+English",
        "Electricity",
        7.0,
    ),
    ComplaintSeed(
        "District B",
        "School-er samne road ta bhanga, children cannot cross safely.",
        "Bengali+English",
        "Road",
        9.0,
        "uploads/sample_pothole_3.jpg",
    ),
    ComplaintSeed(
        "District B",
        "Paani ka colour brown hai, please test the supply urgently.",
        "Hindi+English",
        "Water",
        5.0,
    ),
    ComplaintSeed(
        "District B",
        "Health centre-la emergency doctor illai, patients are being sent far away.",
        "Tamil+English",
        "Healthcare",
        8.0,
    ),
    ComplaintSeed(
        "District B",
        "Street current off hoye geche, electrician ekhono asheni.",
        "Bengali+English",
        "Electricity",
        6.0,
    ),
    ComplaintSeed(
        "District C",
        "Enga colony road full of potholes, ambulance cannot reach us quickly.",
        "Tamil+English",
        "Road",
        10.0,
        "uploads/sample_road_1.jpg",
    ),
    ComplaintSeed(
        "District C",
        "Amader para-te flood water ekhono nameni, families need urgent help.",
        "Bengali+English",
        "Water",
        9.0,
    ),
    ComplaintSeed(
        "District C",
        "Sarkari hospital bahut door hai aur ambulance milti nahi, please help.",
        "Hindi+English",
        "Healthcare",
        8.0,
        "uploads/sample_hospital_1.jpg",
    ),
    ComplaintSeed(
        "District C",
        "Enga village-la transformer damaged, three days without electricity.",
        "Tamil+English",
        "Electricity",
        9.0,
    ),
    ComplaintSeed(
        "District C",
        "Gaon ka bridge road toot gaya hai, school bus cannot pass.",
        "Hindi+English",
        "Road",
        7.0,
    ),
    ComplaintSeed(
        "District C",
        "Jol-er gondho khub kharap, children are falling sick.",
        "Bengali+English",
        "Water",
        10.0,
        "uploads/sample_water_1.jpg",
    ),
    ComplaintSeed(
        "District C",
        "Primary health centre-la beds illa, elderly patients are waiting outside.",
        "Tamil+English",
        "Healthcare",
        8.0,
    ),
    ComplaintSeed(
        "District C",
        "Bijli line dangerous bhabe jhulche, please repair before an accident.",
        "Hindi+Bengali+English",
        "Electricity",
        9.0,
        "uploads/sample_outage_2.mp4",
    ),
)


PROPOSALS: tuple[ProposalSeed, ...] = (
    ProposalSeed("District A", "Main corridor resurfacing and streetlights", 14.0),
    ProposalSeed("District A", "Water pipeline pressure upgrade", 18.0),
    ProposalSeed("District A", "Community clinic equipment renewal", 10.0),
    ProposalSeed("District A", "Transformer replacement program", 12.0),
    ProposalSeed("District B", "School-zone road and drainage repair", 16.0),
    ProposalSeed("District B", "Flood mitigation and stormwater channels", 15.0),
    ProposalSeed("District B", "Ward health-centre expansion", 8.0),
    ProposalSeed("District B", "Electricity reliability upgrades", 14.0),
    ProposalSeed("District C", "Emergency rural road restoration", 13.0),
    ProposalSeed("District C", "Safe drinking-water network", 20.0),
    ProposalSeed("District C", "Primary healthcare access hub", 12.0),
    ProposalSeed("District C", "Village power-line safety project", 11.0),
)


def _get_or_create_district(
    db: Session,
    seed: DistrictSeed,
) -> tuple[District, bool]:
    """Return an existing district or add the requested district."""

    district = db.scalar(select(District).where(District.name == seed.name))
    if district is not None:
        return district, False

    district = District(
        name=seed.name,
        population=seed.population,
        income_level=seed.income_level,
        existing_infra_score=seed.existing_infra_score,
    )
    db.add(district)
    return district, True


def seed_database() -> None:
    """Create demo districts, complaints, and proposals in one transaction."""

    Base.metadata.create_all(bind=engine)
    inserted_districts = 0
    inserted_complaints = 0
    inserted_proposals = 0

    with SessionLocal() as db:
        district_by_name: dict[str, District] = {}
        for district_seed in DISTRICTS:
            district, inserted = _get_or_create_district(db, district_seed)
            district_by_name[district_seed.name] = district
            inserted_districts += int(inserted)

        # Assign IDs to newly added districts before creating foreign-key rows.
        db.flush()

        existing_complaints = {
            complaint.raw_text: complaint
            for complaint in db.scalars(select(Complaint)).all()
        }
        existing_complaint_texts = set(existing_complaints)
        for complaint_seed in COMPLAINTS:
            latitude, longitude = DISTRICT_COORDINATES[complaint_seed.district_name]
            existing_complaint = existing_complaints.get(complaint_seed.raw_text)
            if existing_complaint is not None:
                # Repair legacy demo rows created before geocoding became
                # required, while keeping the seeder idempotent.
                existing_complaint.latitude = latitude
                existing_complaint.longitude = longitude
                existing_complaint.formatted_address = complaint_seed.district_name
                existing_complaint.district_id = district_by_name[
                    complaint_seed.district_name
                ].id
                continue

            db.add(
                Complaint(
                    raw_text=complaint_seed.raw_text,
                    language_detected=complaint_seed.language_detected,
                    category=complaint_seed.category,
                    urgency_score=complaint_seed.urgency_score,
                    latitude=latitude,
                    longitude=longitude,
                    formatted_address=complaint_seed.district_name,
                    evidence_file_path=complaint_seed.evidence_file_path,
                    district_id=district_by_name[
                        complaint_seed.district_name
                    ].id,
                )
            )
            existing_complaint_texts.add(complaint_seed.raw_text)
            inserted_complaints += 1

        # Proposals are attached to the current map-based location clusters.
        # The demo complaints use one shared coordinate per district, so each
        # district resolves to one stable cluster after the complaint flush.
        db.flush()
        clusters_by_district = {
            cluster["district_id"]: cluster["cluster_id"]
            for cluster in get_all_location_clusters(db)
            if cluster.get("district_id") is not None
        }
        cluster_by_district_name = {
            district_name: clusters_by_district[district.id]
            for district_name, district in district_by_name.items()
            if district.id in clusters_by_district
        }

        existing_proposal_keys = {
            (proposal.cluster_id, proposal.project_name)
            for proposal in db.scalars(select(Proposal)).all()
        }
        for proposal_seed in PROPOSALS:
            cluster_id = cluster_by_district_name[proposal_seed.district_name]
            proposal_key = (cluster_id, proposal_seed.project_name)
            if proposal_key in existing_proposal_keys:
                continue

            db.add(
                Proposal(
                    cluster_id=cluster_id,
                    project_name=proposal_seed.project_name,
                    requested_amount=proposal_seed.requested_amount,
                )
            )
            existing_proposal_keys.add(proposal_key)
            inserted_proposals += 1

        db.commit()

    total_requested = sum(proposal.requested_amount for proposal in PROPOSALS)
    print("Seed complete.")
    print(f"Districts inserted: {inserted_districts}")
    print(f"Complaints inserted: {inserted_complaints}")
    print(f"Proposals inserted: {inserted_proposals}")
    print(
        "Demo proposal total: "
        f"INR {total_requested:.2f} crore against an INR 100.00 crore budget."
    )


if __name__ == "__main__":
    seed_database()
