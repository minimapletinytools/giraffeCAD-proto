"""Tests for code_goes_here.blueprint — STL (and STEP guard) export."""

import os
import sys
import tempfile
from pathlib import Path

import pytest
from sympy import Integer

from code_goes_here.blueprint import (
    export_cut_timber_stl,
    export_frame_stl,
    _TRIMESH_AVAILABLE,
    _CADQUERY_AVAILABLE,
)
from code_goes_here.timber import CutTimber, Frame, Timber, timber_from_directions
from code_goes_here.rule import create_v3, create_v2


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------

def _simple_timber(name: str = "test_timber") -> Timber:
    """A small axis-aligned timber for export tests."""
    return timber_from_directions(
        bottom_position=create_v3(Integer(0), Integer(0), Integer(0)),
        length=Integer(2),
        size=create_v2(Integer(1), Integer(1)),
        length_direction=create_v3(Integer(1), Integer(0), Integer(0)),
        width_direction=create_v3(Integer(0), Integer(1), Integer(0)),
        ticket=name,
    )


def _simple_cut_timber(name: str = "test_timber") -> CutTimber:
    return CutTimber(_simple_timber(name))


def _simple_frame() -> Frame:
    t1 = _simple_timber("beam")
    t2 = timber_from_directions(
        bottom_position=create_v3(Integer(0), Integer(0), Integer(0)),
        length=Integer(3),
        size=create_v2(Integer(1), Integer(1)),
        length_direction=create_v3(Integer(0), Integer(0), Integer(1)),
        width_direction=create_v3(Integer(1), Integer(0), Integer(0)),
        ticket="post",
    )
    return Frame(cut_timbers=[CutTimber(t1), CutTimber(t2)], name="TestFrame")


# ---------------------------------------------------------------------------
# STL export — single CutTimber
# ---------------------------------------------------------------------------


@pytest.mark.skipif(not _TRIMESH_AVAILABLE, reason="trimesh not installed")
class TestExportCutTimberStl:
    def test_creates_stl_file(self):
        ct = _simple_cut_timber()
        with tempfile.TemporaryDirectory() as td:
            dest = Path(td) / "out.stl"
            export_cut_timber_stl(ct, dest)
            assert dest.exists()
            assert dest.stat().st_size > 0

    def test_creates_parent_directories(self):
        ct = _simple_cut_timber()
        with tempfile.TemporaryDirectory() as td:
            dest = Path(td) / "sub" / "dir" / "out.stl"
            export_cut_timber_stl(ct, dest)
            assert dest.exists()

    def test_stl_is_valid_trimesh(self):
        """The written STL should be re-loadable by trimesh."""
        import trimesh

        ct = _simple_cut_timber()
        with tempfile.TemporaryDirectory() as td:
            dest = Path(td) / "out.stl"
            export_cut_timber_stl(ct, dest)
            mesh = trimesh.load(str(dest), file_type="stl")
            assert len(mesh.faces) > 0
            assert len(mesh.vertices) > 0


# ---------------------------------------------------------------------------
# STL export — Frame
# ---------------------------------------------------------------------------


@pytest.mark.skipif(not _TRIMESH_AVAILABLE, reason="trimesh not installed")
class TestExportFrameStl:
    def test_creates_one_file_per_timber(self):
        frame = _simple_frame()
        with tempfile.TemporaryDirectory() as td:
            written = export_frame_stl(frame, td)
            assert len(written) == 2
            for p in written:
                assert p.exists()
                assert p.suffix == ".stl"

    def test_file_names_match_timber_names(self):
        frame = _simple_frame()
        with tempfile.TemporaryDirectory() as td:
            written = export_frame_stl(frame, td)
            names = sorted(p.stem for p in written)
            assert names == ["beam", "post"]

    def test_combined_flag(self):
        frame = _simple_frame()
        with tempfile.TemporaryDirectory() as td:
            written = export_frame_stl(frame, td, combined=True)
            # 2 individual + 1 combined = 3
            assert len(written) == 3
            combined = [p for p in written if p.stem == "_combined"]
            assert len(combined) == 1
            assert combined[0].stat().st_size > 0

    def test_creates_output_directory(self):
        frame = _simple_frame()
        with tempfile.TemporaryDirectory() as td:
            out = Path(td) / "new_dir"
            written = export_frame_stl(frame, out)
            assert out.is_dir()
            assert len(written) == 2


# ---------------------------------------------------------------------------
# STEP export — guard when cadquery is missing
# ---------------------------------------------------------------------------


class TestStepImportGuard:
    """Ensure STEP functions raise ImportError when cadquery is unavailable."""

    @pytest.mark.skipif(_CADQUERY_AVAILABLE, reason="cadquery IS installed")
    def test_export_cut_timber_step_raises(self):
        from code_goes_here.blueprint import export_cut_timber_step

        ct = _simple_cut_timber()
        with pytest.raises(ImportError, match="cadquery"):
            export_cut_timber_step(ct, "/tmp/nope.step")

    @pytest.mark.skipif(_CADQUERY_AVAILABLE, reason="cadquery IS installed")
    def test_export_frame_step_raises(self):
        from code_goes_here.blueprint import export_frame_step

        frame = _simple_frame()
        with pytest.raises(ImportError, match="cadquery"):
            export_frame_step(frame, "/tmp/nope_dir")


# ---------------------------------------------------------------------------
# STEP export — oscarshed integration
# ---------------------------------------------------------------------------


@pytest.mark.skipif(not _CADQUERY_AVAILABLE, reason="cadquery not installed")
class TestStepOscarshed:
    """Run STEP export on the full oscarshed frame to catch OCP/cadquery issues."""

    @pytest.fixture(scope="class")
    def oscarshed_frame(self):
        sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "patterns" / "structures"))
        from oscarshed import create_oscarshed
        return create_oscarshed()

    def test_export_single_timber_step(self, oscarshed_frame):
        from code_goes_here.blueprint import export_cut_timber_step

        ct = oscarshed_frame.cut_timbers[0]
        with tempfile.TemporaryDirectory() as td:
            dest = Path(td) / "timber.step"
            export_cut_timber_step(ct, dest)
            assert dest.exists()
            assert dest.stat().st_size > 0

    def test_export_all_timbers_step(self, oscarshed_frame):
        from code_goes_here.blueprint import export_frame_step

        with tempfile.TemporaryDirectory() as td:
            written = export_frame_step(oscarshed_frame, td)
            assert len(written) == len(oscarshed_frame.cut_timbers)
            for p in written:
                assert p.exists()
                assert p.stat().st_size > 0
                assert p.suffix == ".step"
