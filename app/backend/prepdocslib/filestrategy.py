import hashlib
import json
import logging
from typing import Optional

from .blobmanager import AdlsBlobManager, BaseBlobManager, BlobManager
from .embeddings import ImageEmbeddings, OpenAIEmbeddings
from .figureprocessor import (
    FigureProcessor,
    MediaDescriptionStrategy,
    process_page_image,
)
from .fileprocessor import FileProcessor
from .listfilestrategy import File, ListFileStrategy
from .mediadescriber import ContentUnderstandingDescriber
from .searchmanager import SearchManager, Section
from .strategy import DocumentAction, SearchInfo, Strategy
from .textprocessor import process_text

logger = logging.getLogger("scripts")


async def parse_file(
    file: File,
    file_processors: dict[str, FileProcessor],
    category: Optional[str] = None,
    blob_manager: Optional[BaseBlobManager] = None,
    image_embeddings_client: Optional[ImageEmbeddings] = None,
    figure_processor: Optional[FigureProcessor] = None,
    user_oid: Optional[str] = None,
    upload_images: bool = True,
) -> list[Section]:

    key = file.file_extension().lower()
    processor = file_processors.get(key)
    if processor is None:
        logger.info("Skipping '%s', no parser found.", file.filename())
        return []
    logger.info("Ingesting '%s'", file.filename())
    pages = [page async for page in processor.parser.parse(content=file.content)]
    for page in pages:
        for image in page.images:
            logger.info("Processing image '%s' on page %d", image.filename, page.page_num)
            await process_page_image(
                image=image,
                document_filename=file.filename(),
                blob_manager=blob_manager,
                image_embeddings_client=image_embeddings_client,
                figure_processor=figure_processor,
                user_oid=user_oid,
                upload_image=upload_images,
            )
    sections = process_text(pages, file, processor.splitter, category)
    return sections


class FileStrategy(Strategy):
    """
    Strategy for ingesting documents into a search service from files stored either locally or in a data lake storage account
    """

    def __init__(
        self,
        list_file_strategy: ListFileStrategy,
        blob_manager: BlobManager,
        search_info: SearchInfo,
        file_processors: dict[str, FileProcessor],
        document_action: DocumentAction = DocumentAction.Add,
        embeddings: Optional[OpenAIEmbeddings] = None,
        image_embeddings: Optional[ImageEmbeddings] = None,
        search_analyzer_name: Optional[str] = None,
        search_field_name_embedding: Optional[str] = None,
        use_acls: bool = False,
        category: Optional[str] = None,
        figure_processor: Optional[FigureProcessor] = None,
        enforce_access_control: bool = False,
        use_web_source: bool = False,
        use_sharepoint_source: bool = False,
        skip_ingested: bool = False,
    ):
        self.list_file_strategy = list_file_strategy
        self.blob_manager = blob_manager
        self.file_processors = file_processors
        self.document_action = document_action
        self.embeddings = embeddings
        self.image_embeddings = image_embeddings
        self.search_analyzer_name = search_analyzer_name
        self.search_field_name_embedding = search_field_name_embedding
        self.search_info = search_info
        self.use_acls = use_acls
        self.category = category
        self.figure_processor = figure_processor
        self.enforce_access_control = enforce_access_control
        self.use_web_source = use_web_source
        self.use_sharepoint_source = use_sharepoint_source
        self.skip_ingested = skip_ingested

    def ingestion_fingerprint(self, file: File) -> str:
        processor = self.file_processors.get(file.file_extension().lower())
        settings = {
            "version": 1,
            "search_endpoint": self.search_info.endpoint,
            "search_index": self.search_info.index_name,
            "embedding_field": self.search_field_name_embedding,
            "embeddings": (
                {
                    "endpoint": self.embeddings.azure_endpoint,
                    "deployment": self.embeddings.azure_deployment_name,
                    "model": self.embeddings.open_ai_model_name,
                    "dimensions": self.embeddings.open_ai_dimensions,
                }
                if self.embeddings
                else None
            ),
            "category": self.category,
            "acls": file.acls,
            "use_acls": self.use_acls,
            "enforce_access_control": self.enforce_access_control,
            "parser": type(processor.parser).__qualname__ if processor else None,
            "csv_max_chars_per_page": getattr(processor.parser, "max_chars_per_page", None) if processor else None,
            "splitter": type(processor.splitter).__qualname__ if processor else None,
            "splitter_options": (
                {
                    name: getattr(processor.splitter, name, None)
                    for name in (
                        "max_object_length",
                        "max_section_length",
                        "max_tokens_per_section",
                        "section_overlap",
                        "semantic_overlap_percent",
                        "sentence_search_limit",
                    )
                }
                if processor
                else None
            ),
        }
        digest = hashlib.sha256(json.dumps(settings, sort_keys=True).encode("utf-8"))
        file.content.seek(0)
        while chunk := file.content.read(1024 * 1024):
            digest.update(chunk)
        file.content.seek(0)
        return digest.hexdigest()

    async def already_ingested(self, file: File, fingerprint: str) -> bool:
        metadata = await self.blob_manager.get_ingestion_metadata(file)
        count = metadata.get("ingestion_sections", "")
        if metadata.get("ingestion_fingerprint") != fingerprint or not count.isdecimal():
            return False
        section_count = int(count)
        ids = await self.search_manager.get_content_ids(file)
        prefix = f"{file.filename_to_id()}-page-"
        return len(ids) == section_count and all(f"{prefix}{index}" in ids for index in range(section_count))

    def setup_search_manager(self):
        self.search_manager = SearchManager(
            self.search_info,
            self.search_analyzer_name,
            self.use_acls,
            False,  # use_parent_index_projection disabled for file-based ingestion
            self.embeddings,
            field_name_embedding=self.search_field_name_embedding,
            search_images=self.image_embeddings is not None,
            enforce_access_control=self.enforce_access_control,
            use_web_source=self.use_web_source,
            use_sharepoint_source=self.use_sharepoint_source,
        )

    async def setup(self):
        self.setup_search_manager()
        await self.search_manager.create_index()

        if (
            self.figure_processor is not None
            and self.figure_processor.strategy == MediaDescriptionStrategy.CONTENTUNDERSTANDING
        ):
            media_describer = await self.figure_processor.get_media_describer()
            if isinstance(media_describer, ContentUnderstandingDescriber):
                await media_describer.create_analyzer()
                self.figure_processor.mark_content_understanding_ready()

    async def run(self):
        self.setup_search_manager()
        if self.document_action == DocumentAction.Add:
            files = self.list_file_strategy.list()
            processed = 0
            skipped = 0
            async for file in files:
                try:
                    fingerprint = self.ingestion_fingerprint(file) if self.skip_ingested else None
                    if fingerprint is not None and await self.already_ingested(file, fingerprint):
                        logger.info(
                            "Skipping '%s': unchanged content is already uploaded and indexed.", file.filename()
                        )
                        skipped += 1
                        continue
                    blob_url = await self.blob_manager.upload_blob(file)
                    sections = await parse_file(
                        file,
                        self.file_processors,
                        self.category,
                        self.blob_manager,
                        self.image_embeddings,
                        figure_processor=self.figure_processor,
                        upload_images=self.image_embeddings is not None,
                    )
                    if sections:
                        await self.search_manager.update_content(sections, url=blob_url)
                    if fingerprint is not None:
                        await self.search_manager.remove_stale_content(file, len(sections))
                        await self.blob_manager.mark_ingested(file, fingerprint, len(sections))
                    processed += 1
                finally:
                    if file:
                        file.close()
            if self.skip_ingested:
                if not processed and not skipped:
                    raise ValueError("No input documents matched the ingestion file pattern.")
                logger.info("Ingestion complete: %d processed, %d already uploaded and indexed.", processed, skipped)
        elif self.document_action == DocumentAction.Remove:
            paths = self.list_file_strategy.list_paths()
            async for path in paths:
                await self.blob_manager.remove_blob(path)
                await self.search_manager.remove_content(path)
        elif self.document_action == DocumentAction.RemoveAll:
            await self.blob_manager.remove_blob()
            await self.search_manager.remove_content()


class UploadUserFileStrategy:
    """
    Strategy for ingesting a file that has already been uploaded to a ADLS2 storage account
    """

    def __init__(
        self,
        search_info: SearchInfo,
        file_processors: dict[str, FileProcessor],
        blob_manager: AdlsBlobManager,
        search_field_name_embedding: Optional[str] = None,
        embeddings: Optional[OpenAIEmbeddings] = None,
        image_embeddings: Optional[ImageEmbeddings] = None,
        enforce_access_control: bool = False,
        figure_processor: Optional[FigureProcessor] = None,
    ):
        self.file_processors = file_processors
        self.embeddings = embeddings
        self.image_embeddings = image_embeddings
        self.search_info = search_info
        self.blob_manager = blob_manager
        self.figure_processor = figure_processor
        self.search_manager = SearchManager(
            search_info=self.search_info,
            search_analyzer_name=None,
            use_acls=True,
            use_parent_index_projection=False,
            embeddings=self.embeddings,
            field_name_embedding=search_field_name_embedding,
            search_images=image_embeddings is not None,
            enforce_access_control=enforce_access_control,
        )
        self.search_field_name_embedding = search_field_name_embedding

    async def add_file(self, file: File, user_oid: str):
        sections = await parse_file(
            file,
            self.file_processors,
            None,
            self.blob_manager,
            self.image_embeddings,
            figure_processor=self.figure_processor,
            user_oid=user_oid,
            upload_images=self.image_embeddings is not None,
        )
        if sections:
            await self.search_manager.update_content(sections, url=file.url)

    async def remove_file(self, filename: str, oid: str):
        if filename is None or filename == "":
            logging.warning("Filename is required to remove a file")
            return
        await self.search_manager.remove_content(filename, oid)
