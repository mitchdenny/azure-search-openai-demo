import hashlib
import logging
from io import BytesIO
from unittest.mock import MagicMock

import pytest
from azure.core.exceptions import HttpResponseError, ResourceNotFoundError
from azure.search.documents.aio import SearchClient
from azure.search.documents.models import IndexingResult
from azure.storage.blob import BlobProperties
from azure.storage.blob.aio import BlobClient, ContainerClient

from prepdocslib.blobmanager import BlobManager
from prepdocslib.embeddings import OpenAIEmbeddings
from prepdocslib.fileprocessor import FileProcessor
from prepdocslib.filestrategy import FileStrategy
from prepdocslib.listfilestrategy import File, LocalListFileStrategy
from prepdocslib.strategy import SearchInfo
from prepdocslib.textparser import TextParser
from prepdocslib.textsplitter import SimpleTextSplitter

from .mocks import MockAzureCredential


@pytest.fixture
def ingestion_cloud(monkeypatch, tmp_path):
    state = {
        "blobs": {},
        "documents": {},
        "uploads": 0,
        "embeddings": 0,
        "reject": False,
        "read_error": None,
        "delete_error": False,
    }

    async def exists(self):
        return True

    async def upload(self, name, data, **kwargs):
        state["uploads"] += 1
        state["blobs"][name] = {"content": data.read(), "metadata": {}}
        return self.get_blob_client(name)

    async def get_properties(self, **kwargs):
        if state["read_error"]:
            raise state["read_error"]
        if self.blob_name not in state["blobs"]:
            raise ResourceNotFoundError("Blob does not exist")
        return BlobProperties(metadata=dict(state["blobs"][self.blob_name]["metadata"]))

    async def set_metadata(self, metadata, **kwargs):
        state["blobs"][self.blob_name]["metadata"] = dict(metadata)

    async def upload_documents(self, documents, **kwargs):
        results = []
        for document in documents:
            succeeded = not state["reject"]
            if succeeded:
                state["documents"][document["id"]] = document
            results.append(
                IndexingResult(
                    key=document["id"],
                    succeeded=succeeded,
                    error_message=None if succeeded else "Indexing failed",
                )
            )
        return results

    async def search(self, *, search_text, filter, select, top=50, skip=0):
        assert select == ["id"]
        filename = filter[len("sourcefile eq '") : -1].replace("''", "'")
        documents = [document for document in state["documents"].values() if document["sourcefile"] == filename]

        async def results():
            for document in documents[skip : skip + top]:
                yield {"id": document["id"]}

        return results()

    async def delete(self, documents, **kwargs):
        if state["delete_error"]:
            return [
                IndexingResult(key=document["id"], succeeded=False, error_message="Delete failed")
                for document in documents
            ]
        for document in documents:
            del state["documents"][document["id"]]
        return [IndexingResult(key=document["id"], succeeded=True) for document in documents]

    async def create_embeddings(texts):
        state["embeddings"] += len(texts)
        return [[0.1, 0.2, 0.3] for text in texts]

    monkeypatch.setattr(ContainerClient, "exists", exists)
    monkeypatch.setattr(ContainerClient, "upload_blob", upload)
    monkeypatch.setattr(BlobClient, "get_blob_properties", get_properties)
    monkeypatch.setattr(BlobClient, "set_blob_metadata", set_metadata)
    monkeypatch.setattr(SearchClient, "upload_documents", upload_documents)
    monkeypatch.setattr(SearchClient, "search", search)
    monkeypatch.setattr(SearchClient, "delete_documents", delete)

    def make_strategy(index="test", max_object_length=5):
        embeddings = OpenAIEmbeddings(
            MagicMock(),
            "text-embedding-3-small",
            3,
            azure_endpoint="https://openai.example.com",
            azure_deployment_name="embeddings",
        )
        monkeypatch.setattr(embeddings, "create_embeddings", create_embeddings)
        return FileStrategy(
            LocalListFileStrategy(str(tmp_path / "*.txt"), use_cache=False),
            BlobManager("https://storage.blob.core.windows.net", "content", MockAzureCredential()),
            SearchInfo("https://search.search.windows.net", MockAzureCredential(), index),
            {".txt": FileProcessor(TextParser(), SimpleTextSplitter(max_object_length))},
            embeddings=embeddings,
            search_field_name_embedding="embedding",
            skip_ingested=True,
        )

    return state, make_strategy


@pytest.mark.asyncio
async def test_ingestion_checkpoint_skips_completed_content(ingestion_cloud, tmp_path, caplog):
    state, make_strategy = ingestion_cloud
    path = tmp_path / "sample.txt"
    path.write_text("abcdef")
    with caplog.at_level(logging.INFO, logger="scripts"):
        await make_strategy().run()
        await make_strategy().run()
    assert state["uploads"] == 1
    assert state["embeddings"] == 2
    assert state["blobs"]["sample.txt"]["content"] == b"abcdef"
    assert "0 processed, 1 already uploaded and indexed" in caplog.text
    assert not (tmp_path / "sample.txt.md5").exists()


@pytest.mark.asyncio
@pytest.mark.parametrize("change", ["content", "blob", "sections", "index", "splitter", "model", "metadata"])
async def test_ingestion_checkpoint_reprocesses_missing_or_changed_content(ingestion_cloud, tmp_path, change):
    state, make_strategy = ingestion_cloud
    path = tmp_path / "sample.txt"
    path.write_text("abcdef")
    await make_strategy().run()
    strategy = make_strategy()
    if change == "content":
        path.write_text("ghijkl")
    elif change == "blob":
        del state["blobs"]["sample.txt"]
    elif change == "sections":
        state["documents"].clear()
    elif change == "index":
        strategy = make_strategy(index="new-index")
    elif change == "splitter":
        strategy = make_strategy(max_object_length=3)
    elif change == "model":
        strategy.embeddings.azure_deployment_name = "new-embeddings"
    else:
        state["blobs"]["sample.txt"]["metadata"]["ingestion_sections"] = "invalid"
    await strategy.run()
    assert state["uploads"] == 2
    assert state["embeddings"] == 4


@pytest.mark.asyncio
async def test_ingestion_checkpoint_replaces_stale_sections(ingestion_cloud, tmp_path):
    state, make_strategy = ingestion_cloud
    path = tmp_path / "sample.txt"
    path.write_text("abcdefghijk")
    await make_strategy().run()
    assert len(state["documents"]) == 3
    path.write_text("new")
    await make_strategy().run()
    await make_strategy().run()
    assert len(state["documents"]) == 1
    assert next(iter(state["documents"].values()))["content"] == "new"
    assert state["embeddings"] == 4
    assert state["uploads"] == 2


@pytest.mark.asyncio
async def test_ingestion_checkpoint_does_not_trust_local_md5(ingestion_cloud, tmp_path):
    state, make_strategy = ingestion_cloud
    (tmp_path / "sample.txt").write_text("sample")
    md5 = tmp_path / "sample.txt.md5"
    md5.write_text(hashlib.md5(b"sample").hexdigest())
    await make_strategy().run()
    assert state["uploads"] == 1
    assert len(state["documents"]) == 2
    assert md5.read_text() == hashlib.md5(b"sample").hexdigest()


@pytest.mark.asyncio
async def test_ingestion_checkpoint_preserves_completed_files_after_failure(ingestion_cloud, tmp_path):
    state, make_strategy = ingestion_cloud
    (tmp_path / "complete.txt").write_text("done")
    await make_strategy().run()
    (tmp_path / "retry.txt").write_text("retry")
    state["reject"] = True
    with pytest.raises(RuntimeError, match="Indexing failed"):
        await make_strategy().run()
    assert state["blobs"]["retry.txt"]["metadata"] == {}
    assert state["blobs"]["complete.txt"]["metadata"]["ingestion_fingerprint"]
    state["reject"] = False
    await make_strategy().run()
    assert state["uploads"] == 3
    assert state["embeddings"] == 3
    assert state["blobs"]["retry.txt"]["metadata"]["ingestion_fingerprint"]


@pytest.mark.asyncio
async def test_ingestion_checkpoint_surfaces_authorization_errors(ingestion_cloud, tmp_path):
    state, make_strategy = ingestion_cloud
    (tmp_path / "sample.txt").write_text("sample")
    state["read_error"] = HttpResponseError("Storage access denied")
    with pytest.raises(HttpResponseError, match="Storage access denied"):
        await make_strategy().run()
    assert state["embeddings"] == 0
    assert state["uploads"] == 0


@pytest.mark.asyncio
async def test_ingestion_checkpoint_does_not_record_failed_cleanup(ingestion_cloud, tmp_path):
    state, make_strategy = ingestion_cloud
    path = tmp_path / "sample.txt"
    path.write_text("abcdefghijk")
    await make_strategy().run()
    path.write_text("new")
    state["delete_error"] = True
    with pytest.raises(RuntimeError, match="Delete failed"):
        await make_strategy().run()
    assert state["blobs"]["sample.txt"]["metadata"] == {}


@pytest.mark.asyncio
async def test_ingestion_checkpoint_rejects_missing_input(ingestion_cloud):
    _, make_strategy = ingestion_cloud
    with pytest.raises(ValueError, match="No input documents matched"):
        await make_strategy().run()


@pytest.mark.asyncio
async def test_ingestion_checkpoint_preserves_other_blob_metadata(ingestion_cloud):
    state, make_strategy = ingestion_cloud
    state["blobs"]["sample.txt"] = {"content": b"sample", "metadata": {"owner": "demo"}}
    content = BytesIO(b"sample")
    content.name = "sample.txt"
    await make_strategy().blob_manager.mark_ingested(File(content), "fingerprint", 2)
    assert state["blobs"]["sample.txt"]["metadata"] == {
        "owner": "demo",
        "ingestion_fingerprint": "fingerprint",
        "ingestion_sections": "2",
    }


@pytest.mark.asyncio
async def test_ingestion_checkpoint_escapes_quoted_filenames(ingestion_cloud, tmp_path):
    state, make_strategy = ingestion_cloud
    (tmp_path / "o'brien.txt").write_text("sample")
    await make_strategy().run()
    await make_strategy().run()
    assert state["uploads"] == 1
    assert state["embeddings"] == 2


@pytest.mark.asyncio
@pytest.mark.parametrize("sections", [55, 1001])
async def test_ingestion_checkpoint_checks_all_search_result_pages(ingestion_cloud, tmp_path, sections):
    state, make_strategy = ingestion_cloud
    (tmp_path / "sample.txt").write_text("a" * sections)
    await make_strategy(max_object_length=1).run()
    await make_strategy(max_object_length=1).run()
    assert state["uploads"] == 1
    assert state["embeddings"] == sections
    assert len(state["documents"]) == sections
