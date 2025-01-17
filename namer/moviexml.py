"""
Reads movie.xml (your.movie.name.nfo) of Emby/Jellyfin format in to a LookedUpFileInfo,
allowing the metadata to be written in to video files (currently only mp4's),
or used in renaming the video file.
"""
from pathlib import Path
from typing import Any, Optional

from lxml import etree, objectify

from namer.configuration import NamerConfig
from namer.command import set_permissions
from namer.comparison_results import LookedUpFileInfo, Performer


def parse_movie_xml_file(xml_file: Path) -> LookedUpFileInfo:
    """
    Parse an Emby/Jellyfin xml file and creates a LookedUpFileInfo from the data.
    """
    content = xml_file.read_text(encoding="UTF-8")

    movie: Any = objectify.fromstring(bytes(content, encoding="UTF-8"), parser=None)
    info = LookedUpFileInfo()
    info.name = str(movie.title)
    info.site = str(movie.studio[0])
    info.date = str(movie.releasedate)
    info.description = str(movie.plot)
    info.poster_url = str(movie.art.poster)

    info.performers = []
    for actor in movie.actor:
        if actor is not None and actor.name:
            performer = Performer(str(actor.name))
            performer.role = str(actor.role)
            info.performers.append(performer)
    if hasattr(movie, "phoenixadulturlid"):
        info.look_up_site_id = str(movie.phoenixadulturlid)

    if hasattr(movie, "theporndbid"):
        info.uuid = str(movie.theporndbid)

    info.tags = []
    for genre in movie.genre:
        info.tags.append(str(genre))

    info.original_parsed_filename = None
    info.original_query = None
    info.original_response = None

    return info


def write_movie_xml_file(info: LookedUpFileInfo, config: NamerConfig, trailer: Optional[Path] = None, poster: Optional[Path] = None, background: Optional[Path] = None) -> str:
    """
    Parse porndb info and create an Emby/Jellyfin xml file from the data.
    """
    root: Any = etree.Element("movie", attrib=None, nsmap=None)
    etree.SubElement(root, "plot", attrib=None, nsmap=None).text = info.description
    etree.SubElement(root, "outline", attrib=None, nsmap=None)
    etree.SubElement(root, "title", attrib=None, nsmap=None).text = info.name
    etree.SubElement(root, "dateadded", attrib=None, nsmap=None)

    trailer_tag = etree.SubElement(root, "trailer", attrib=None, nsmap=None)
    if trailer:
        trailer_tag.text = str(trailer)

    if info.date:
        etree.SubElement(root, "year", attrib=None, nsmap=None).text = info.date[:4]

    etree.SubElement(root, "premiered", attrib=None, nsmap=None).text = info.date
    etree.SubElement(root, "releasedate", attrib=None, nsmap=None).text = info.date
    etree.SubElement(root, "mpaa", attrib=None, nsmap=None).text = "XXX"
    art = etree.SubElement(root, "art", attrib=None, nsmap=None)

    poster_tag = etree.SubElement(art, "poster", attrib=None, nsmap=None)
    if poster:
        poster_tag.text = str(poster)

    background_tag = etree.SubElement(art, "background", attrib=None, nsmap=None)
    if background:
        background_tag.text = str(background)

    if config.enable_metadataapi_genres:
        for tag in info.tags:
            etree.SubElement(root, "genre", attrib=None, nsmap=None).text = tag
    else:
        for tag in info.tags:
            etree.SubElement(root, "tag", attrib=None, nsmap=None).text = tag
        etree.SubElement(root, "genre", attrib=None, nsmap=None).text = config.default_genre

    etree.SubElement(root, "studio", attrib=None, nsmap=None).text = info.site
    etree.SubElement(root, "theporndbid", attrib=None, nsmap=None).text = str(info.uuid)
    etree.SubElement(root, "phoenixadultid", attrib=None, nsmap=None)
    etree.SubElement(root, "phoenixadulturlid", attrib=None, nsmap=None)
    etree.SubElement(root, "sourceid", attrib=None, nsmap=None).text = info.source_url

    for performer in info.performers:
        actor = objectify.SubElement(root, "actor", attrib=None, nsmap=None)
        etree.SubElement(actor, "name", attrib=None, nsmap=None).text = performer.name
        etree.SubElement(actor, "role", attrib=None, nsmap=None).text = performer.role
        etree.SubElement(actor, "image", attrib=None, nsmap=None).text = str(performer.image)
        etree.SubElement(actor, "type", attrib=None, nsmap=None).text = "Actor"
        etree.SubElement(actor, "thumb", attrib=None, nsmap=None)

    objectify.SubElement(root, "fileinfo", attrib=None, nsmap=None)
    objectify.deannotate(root)
    etree.cleanup_namespaces(root, top_nsmap=None, keep_ns_prefixes=None)

    return etree.tostring(root, pretty_print=True, xml_declaration=True, encoding="UTF-8").decode(encoding="UTF-8")  # type: ignore


def write_nfo(video_file: Path, new_metadata: LookedUpFileInfo, namer_config: NamerConfig, trailer: Optional[Path], poster: Optional[Path], background: Optional[Path]):
    """
    Writes an .nfo to the correct place for a video file.
    """
    if video_file and new_metadata and namer_config.write_nfo:
        target = video_file.parent / (video_file.stem + ".nfo")
        with open(target, "wt", encoding="UTF-8") as nfo_file:
            towrite = write_movie_xml_file(new_metadata, namer_config, trailer, poster, background)
            nfo_file.write(towrite)
        set_permissions(target, namer_config)
