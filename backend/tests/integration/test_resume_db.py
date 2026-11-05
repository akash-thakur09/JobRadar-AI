"""Integration tests for Master Resumes and Resume Versions database persistence."""

import uuid

import pytest
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.database.health import check_db_health
from app.database.session import get_session_factory
from app.modules.candidate.models import CandidateProfile, User
from app.modules.resumes.models import MasterResume, ResumeVersion


@pytest.fixture(autouse=True)
async def check_postgres_availability() -> None:
    """Skip integration tests if live PostgreSQL is unreachable."""
    is_healthy, detail = await check_db_health()
    if not is_healthy:
        pytest.skip(f"Live PostgreSQL not reachable ({detail}). Skipping resume DB tests.")


@pytest.mark.integration
async def test_resume_db_lifecycle() -> None:
    """Verify MasterResume and ResumeVersion persistence and querying."""
    session_factory = get_session_factory()

    async with session_factory() as session:
        user = User(email=f"resume_test_{uuid.uuid4()}@jobradar.local", is_active=True)
        session.add(user)
        await session.flush()

        profile = CandidateProfile(
            user_id=user.id,
            full_name="Resume Tester",
            total_experience_months=24,
        )
        session.add(profile)
        await session.flush()
        profile_id = profile.id

        resume = MasterResume(
            candidate_profile_id=profile_id,
            original_filename="resume_test.pdf",
            storage_key=f"resumes/raw/{profile_id}/test.pdf",
            mime_type="application/pdf",
            file_size_bytes=1024,
            checksum_sha256="fakechecksum" + str(uuid.uuid4())[:20],
            is_active=True,
        )
        session.add(resume)
        await session.flush()
        resume_id = resume.id

        version = ResumeVersion(
            master_resume_id=resume_id,
            version_number=1,
            structured_content={"skills": ["python", "fastapi"]},
            template_metadata={"page_count": 1},
            checksum_sha256="versionchecksum" + str(uuid.uuid4())[:15],
            is_valid=True,
            processing_status="COMPLETED",
        )
        session.add(version)
        await session.flush()
        version_id = version.id
        await session.commit()

    # Query back in a new session
    async with session_factory() as session:
        fetched_resume = await session.get(MasterResume, resume_id)
        assert fetched_resume is not None
        assert fetched_resume.is_active is True
        assert len(fetched_resume.versions) == 1
        assert fetched_resume.versions[0].id == version_id
        assert fetched_resume.versions[0].structured_content["skills"] == ["python", "fastapi"]

        # Cleanup created user (cascades to profile, resumes, versions)
        usr = await session.get(User, user.id)
        if usr:
            await session.delete(usr)
            await session.commit()


@pytest.mark.integration
async def test_resume_db_single_active_constraint() -> None:
    """Verify partial unique index prevents multiple active resumes for one candidate."""
    session_factory = get_session_factory()

    async with session_factory() as session:
        user = User(email=f"active_chk_{uuid.uuid4()}@jobradar.local", is_active=True)
        session.add(user)
        await session.flush()

        profile = CandidateProfile(
            user_id=user.id,
            full_name="Active Resume Tester",
            total_experience_months=12,
        )
        session.add(profile)
        await session.flush()
        profile_id = profile.id

        resume1 = MasterResume(
            candidate_profile_id=profile_id,
            original_filename="resume1.pdf",
            storage_key=f"resumes/raw/{profile_id}/1.pdf",
            mime_type="application/pdf",
            file_size_bytes=500,
            checksum_sha256="checksum1" + str(uuid.uuid4())[:20],
            is_active=True,
        )
        session.add(resume1)
        await session.flush()

        # Second active resume for the same candidate profile must violate uq_master_resumes_single_active
        resume2 = MasterResume(
            candidate_profile_id=profile_id,
            original_filename="resume2.pdf",
            storage_key=f"resumes/raw/{profile_id}/2.pdf",
            mime_type="application/pdf",
            file_size_bytes=600,
            checksum_sha256="checksum2" + str(uuid.uuid4())[:20],
            is_active=True,
        )
        session.add(resume2)

        with pytest.raises(IntegrityError):
            await session.flush()

        await session.rollback()


@pytest.mark.integration
async def test_resume_db_version_number_unique_constraint() -> None:
    """Verify unique constraint on (master_resume_id, version_number)."""
    session_factory = get_session_factory()

    async with session_factory() as session:
        user = User(email=f"version_chk_{uuid.uuid4()}@jobradar.local", is_active=True)
        session.add(user)
        await session.flush()

        profile = CandidateProfile(
            user_id=user.id,
            full_name="Version Tester",
            total_experience_months=36,
        )
        session.add(profile)
        await session.flush()

        resume = MasterResume(
            candidate_profile_id=profile.id,
            original_filename="resume.pdf",
            storage_key=f"resumes/raw/{profile.id}/file.pdf",
            mime_type="application/pdf",
            file_size_bytes=500,
            checksum_sha256="checksum_ver" + str(uuid.uuid4())[:20],
            is_active=True,
        )
        session.add(resume)
        await session.flush()

        v1 = ResumeVersion(
            master_resume_id=resume.id,
            version_number=1,
            structured_content={},
            checksum_sha256="v1_checksum" + str(uuid.uuid4())[:20],
        )
        session.add(v1)
        await session.flush()

        # Duplicate version number 1
        v1_dup = ResumeVersion(
            master_resume_id=resume.id,
            version_number=1,
            structured_content={},
            checksum_sha256="v1_dup_checksum" + str(uuid.uuid4())[:16],
        )
        session.add(v1_dup)

        with pytest.raises(IntegrityError):
            await session.flush()

        await session.rollback()


@pytest.mark.integration
async def test_resume_db_cascade_deletion() -> None:
    """Verify deleting CandidateProfile cascades to MasterResume and ResumeVersion."""
    session_factory = get_session_factory()

    async with session_factory() as session:
        user = User(email=f"cascade_res_{uuid.uuid4()}@jobradar.local", is_active=True)
        session.add(user)
        await session.flush()

        profile = CandidateProfile(
            user_id=user.id,
            full_name="Cascade Profile",
            total_experience_months=48,
        )
        session.add(profile)
        await session.flush()
        profile_id = profile.id

        resume = MasterResume(
            candidate_profile_id=profile_id,
            original_filename="cascade_cv.pdf",
            storage_key=f"resumes/raw/{profile_id}/cv.pdf",
            mime_type="application/pdf",
            file_size_bytes=1000,
            checksum_sha256="chk_cascade_" + str(uuid.uuid4())[:20],
            is_active=True,
        )
        session.add(resume)
        await session.flush()
        resume_id = resume.id

        version = ResumeVersion(
            master_resume_id=resume_id,
            version_number=1,
            structured_content={},
            checksum_sha256="chk_ver_cascade_" + str(uuid.uuid4())[:15],
        )
        session.add(version)
        await session.flush()
        version_id = version.id
        await session.commit()

    # Delete candidate profile
    async with session_factory() as session:
        prof = await session.get(CandidateProfile, profile_id)
        assert prof is not None
        await session.delete(prof)
        await session.commit()

    # Verify resume and version are gone
    async with session_factory() as session:
        res_query = await session.execute(select(MasterResume).where(MasterResume.id == resume_id))
        assert res_query.scalar_one_or_none() is None

        ver_query = await session.execute(
            select(ResumeVersion).where(ResumeVersion.id == version_id)
        )
        assert ver_query.scalar_one_or_none() is None
