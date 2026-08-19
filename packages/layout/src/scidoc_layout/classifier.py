from scidoc_core.region import Region, RegionType


def classify_region(region: Region) -> RegionType:
    return region.region_type
