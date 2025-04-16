import pytest
import json
import os
import tempfile
from pathlib import Path


@pytest.mark.asyncio
async def test_get_version(client):
    """Test getting the Reducto API version"""
    response = await client.process_query(
        "Use the get_version tool to check the Reducto API version."
        "and return version with keyword 'version' if successful or error with keyword 'error_message'"
        "sample response: version: value"
    )

    assert "version" in response
    version = response.split("version: ")[1].split("\n")[0].strip()
    assert version, "Version not found in response"

    if "error_message" in response:
        pytest.fail(f"Failed to get version: {response}")

    print(f"✅ Get version completed: {version}")


@pytest.mark.asyncio
async def test_upload_document(client):
    """Test uploading a document to Reducto"""
    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as temp_file:
        temp_file.write(
            b"%PDF-1.7\n1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n2 0 obj\n<< /Type /Pages /Kids [3 0 R] /Count 1 >>\nendobj\n3 0 obj\n<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Contents 4 0 R >>\nendobj\n4 0 obj\n<< /Length 21 >>\nstream\nBT\n/F1 12 Tf\n100 700 Td\n(Test PDF) Tj\nET\nendstream\nendobj\nxref\n0 5\n0000000000 65535 f\n0000000010 00000 n\n0000000060 00000 n\n0000000120 00000 n\n0000000210 00000 n\ntrailer\n<< /Size 5 /Root 1 0 R >>\nstartxref\n290\n%%EOF"
        )
        temp_path = temp_file.name

    response = await client.process_query(
        f"Use the upload_document tool to upload this document to Reducto: {temp_path}"
        f"and return file_id with keyword 'file_id' if successful or error with keyword 'error_message'"
        "sample response: file_id: value"
    )

    if "error_message" in response:
        os.unlink(temp_path)
        pytest.fail(f"Failed to upload document: {response}")

    assert "file_id" in response
    file_id = response.split("file_id: ")[1].split("\n")[0].strip()
    assert file_id, "File ID not found in response"

    os.unlink(temp_path)

    print(f"✅ Document upload completed: {file_id}")
    return file_id


@pytest.mark.asyncio
async def test_parse_document(client):
    """Test parsing a document with Reducto"""
    file_id = await test_upload_document(client)
    if not file_id:
        pytest.skip("Upload failed, cannot proceed with parse test")

    response = await client.process_query(
        f"Use the parse_document tool to parse the document with ID reducto://{file_id} using standard OCR mode."
        f"and return job_id with keyword 'job_id' if successful or error with keyword 'error_message'"
        "sample response: job_id: value"
    )

    if "error_message" in response:
        pytest.fail(f"Failed to parse document: {response}")

    assert "job_id" in response
    job_id = response.split("job_id: ")[1].split("\n")[0].strip()
    assert job_id, "Job ID not found in response"

    print(f"✅ Document parse completed: {job_id}")
    return job_id


@pytest.mark.asyncio
async def test_parse_document_async(client):
    """Test parsing a document asynchronously with Reducto"""
    file_id = await test_upload_document(client)
    if not file_id:
        pytest.skip("Upload failed, cannot proceed with async parse test")

    response = await client.process_query(
        f"Use the parse_document_async tool to parse the document with ID reducto://{file_id} asynchronously."
        f"and return job_id with keyword 'job_id' if successful or error with keyword 'error_message'"
        "sample response: job_id: value"
    )

    if "error_message" in response:
        pytest.fail(f"Failed to parse document asynchronously: {response}")

    assert "job_id" in response
    job_id = response.split("job_id: ")[1].split("\n")[0].strip()
    assert job_id, "Job ID not found in response"

    print(f"✅ Async document parse completed: {job_id}")
    return job_id


@pytest.mark.asyncio
async def test_get_job_status(client):
    """Test checking the status of a job"""
    job_id = await test_parse_document_async(client)
    if not job_id:
        pytest.skip("Could not get job ID, cannot proceed with status check")

    response = await client.process_query(
        f"Use the get_job_status tool to check the status of job {job_id}"
        f"and return status with keyword 'status' if successful or error with keyword 'error_message'"
        "sample response: status: value"
    )

    if "error_message" in response:
        pytest.fail(f"Failed to get job status: {response}")

    assert "status" in response
    status = response.split("status: ")[1].split("\n")[0].strip()
    assert status, "Status not found in response"

    print(f"✅ Job status check completed: {status}")
    return status


@pytest.mark.asyncio
async def test_cancel_job(client):
    """Test canceling a job"""
    job_id = await test_parse_document_async(client)
    if not job_id:
        pytest.skip("Could not get job ID, cannot proceed with cancel test")

    response = await client.process_query(
        f"Use the cancel_job tool to cancel the job with ID {job_id}"
        f"and return result with keyword 'result' if successful or error with keyword 'error_message'"
        "sample response: result: value"
    )

    if "error_message" in response:
        if "completed" in response.lower():
            print(f"⚠️ Job already completed, couldn't cancel: {job_id}")
            return
        pytest.fail(f"Failed to cancel job: {response}")

    assert "result" in response
    result = response.split("result: ")[1].split("\n")[0].strip()

    print(f"✅ Job cancellation completed: {result}")


@pytest.mark.asyncio
async def test_split_document(client):
    """Test splitting a document into sections"""
    file_id = await test_upload_document(client)
    if not file_id:
        pytest.skip("Upload failed, cannot proceed with split test")

    response = await client.process_query(
        f"Use the split_document tool to split the document with ID reducto://{file_id} into sections: Introduction and Conclusion."
        f"and return sections with keyword 'sections' if successful or error with keyword 'error_message'"
        "sample response: sections: value"
    )

    if "error_message" in response:
        pytest.fail(f"Failed to split document: {response}")

    assert "sections" in response

    print(f"✅ Document split completed")


@pytest.mark.asyncio
async def test_split_document_async(client):
    """Test splitting a document asynchronously"""
    file_id = await test_upload_document(client)
    if not file_id:
        pytest.skip("Upload failed, cannot proceed with async split test")

    response = await client.process_query(
        f"Use the split_document_async tool to split the document with ID reducto://{file_id} asynchronously into sections: Introduction and Conclusion."
        f"and return job_id with keyword 'job_id' if successful or error with keyword 'error_message'"
        "sample response: job_id: value"
    )

    if "error_message" in response:
        pytest.fail(f"Failed to split document asynchronously: {response}")

    assert "job_id" in response
    job_id = response.split("job_id: ")[1].split("\n")[0].strip()
    assert job_id, "Job ID not found in response"

    print(f"✅ Async document split completed: {job_id}")
    return job_id


@pytest.mark.asyncio
async def test_extract_data(client):
    """Test extracting structured data from a document"""
    job_id = await test_parse_document(client)
    if not job_id:
        pytest.skip("Parse failed, cannot proceed with extract test")

    schema = {
        "type": "object",
        "properties": {"title": {"type": "string"}, "content": {"type": "string"}},
    }

    response = await client.process_query(
        f"Use the extract_data tool to extract data from document with job ID jobid://{job_id} using schema: {json.dumps(schema)}"
        f"and return extracted data with keyword 'data' if successful or error with keyword 'error_message'"
        "sample response: data: value"
    )

    if "error_message" in response:
        pytest.fail(f"Failed to extract data: {response}")

    assert "data" in response

    print(f"✅ Data extraction completed")


@pytest.mark.asyncio
async def test_extract_data_async(client):
    """Test extracting structured data asynchronously"""
    job_id = await test_parse_document(client)
    if not job_id:
        pytest.skip("Parse failed, cannot proceed with async extract test")

    schema = {
        "type": "object",
        "properties": {"title": {"type": "string"}, "content": {"type": "string"}},
    }

    response = await client.process_query(
        f"Use the extract_data_async tool to extract data asynchronously from document with job ID jobid://{job_id} using schema: {json.dumps(schema)}"
        f"and return job_id with keyword 'job_id' if successful or error with keyword 'error_message'"
        "sample response: job_id: value"
    )

    if "error_message" in response:
        pytest.fail(f"Failed to extract data asynchronously: {response}")

    assert "job_id" in response
    job_id = response.split("job_id: ")[1].split("\n")[0].strip()
    assert job_id, "Job ID not found in response"

    print(f"✅ Async data extraction completed: {job_id}")
    return job_id


@pytest.mark.asyncio
async def test_webhook_portal(client):
    """Test configuring the webhook portal"""
    response = await client.process_query(
        "Use the webhook_portal tool to configure the webhook portal."
        "and return result with keyword 'result' if successful or error with keyword 'error_message'"
        "sample response: result: value"
    )

    if "error_message" in response:
        pytest.fail(f"Failed to configure webhook portal: {response}")

    assert "result" in response
    result = response.split("result: ")[1].split("\n")[0].strip()

    print(f"✅ Webhook portal configuration completed: {result}")


@pytest.mark.asyncio
async def test_document_flow(client):
    """Test a document processing flow: upload → parse → extract"""
    file_id = await test_upload_document(client)
    if not file_id:
        pytest.skip("Upload failed, cannot proceed with flow test")

    response = await client.process_query(
        f"Use the parse_document_async tool to parse the document with ID reducto://{file_id} asynchronously."
        f"and return job_id with keyword 'job_id' if successful or error with keyword 'error_message'"
        "sample response: job_id: value"
    )

    if "error_message" in response:
        pytest.fail(f"Failed to parse document in flow test: {response}")

    assert "job_id" in response
    job_id = response.split("job_id: ")[1].split("\n")[0].strip()
    assert job_id, "Job ID not found in parse response"

    status_response = await client.process_query(
        f"Use the get_job_status tool to check the status of job {job_id}"
        f"and return status with keyword 'status' if successful or error with keyword 'error_message'"
    )

    if "error_message" in status_response:
        pytest.fail(f"Failed to get job status in flow test: {status_response}")

    assert "status" in status_response
    status = status_response.split("status: ")[1].split("\n")[0].strip()

    print(f"✅ Document flow test completed with status: {status}")
