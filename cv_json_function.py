from docling.document_converter import DocumentConverter
from docling.datamodel.base_models import InputFormat
from docling.document_converter import DocumentConverter, PdfFormatOption
from docling.datamodel.pipeline_options import PdfPipelineOptions, TableFormerMode
from dotenv import load_dotenv
import json
from openai import OpenAI
import os
from fastapi import HTTPException
import aiofiles
from dict_file import mapping_dict
load_dotenv()

async def cv_json(file_path):
    if not (file_path.endswith(".pdf") or file_path.endswith(".docx")):
        raise HTTPException(status_code=400, detail="Only PDF and Word documents are allowed")
    pipeline_options = PdfPipelineOptions(do_table_structure=True)
    pipeline_options.table_structure_options.mode = TableFormerMode.ACCURATE  # use more accurate TableFormer model
    source = file_path  # Update with the actual path to the resume PDF
    converter = DocumentConverter(format_options={InputFormat.PDF: PdfFormatOption(pipeline_options=pipeline_options)})
    result = converter.convert(source)  
    markdown_text = result.document.export_to_markdown()

    # Load JSON template
    # json_template_path = r"D:\OneDrive - MariApps Marine Solutions Pte.Ltd\liju_resume_parser/output_json.json"
    # with open(json_template_path, "r", encoding="utf-8") as file:
    #     json_template_str = json.load(file)

    async with aiofiles.open("output_json.json", "r", encoding="utf-8") as file:
        json_template_str = json.loads(await file.read())
    
    prompt = f"""
    You are an expert in data extraction and JSON formatting. Your task is to extract and format resume data **exactly** as per the provided JSON template `{json_template_str}`. Ensure strict compliance with structure, accuracy, and completeness. Follow these rules carefully:
    ### **Extraction Guidelines:**
    1. **Strict JSON Compliasnce:**
    - Every key in smaple JSON must be present, even if values are `null`. 
    - Maintain exact order and structure—no extra details or modifications.
    - Tables (`basic_details`, `experience_table`, `certificate_table`) should strictly follow the provided format.  
    2. **Data Handling Rules:**
    - **basic_details:**  Extract all the basic details includes the name, address, `City`, `State`, `Country`, Zipcode etc and map it to the specific fields. Split the address into Address1–Address4.
    - **Experience Table:**
        - Merge multi-line entries into complete, single values.
        - Ensure `TEU` (container capacity) is numerical and `IMO` is a 7-digit number. If missing, set to `null`.
        - Ensure `Flag` values are valid country names (e.g., "Panama"), otherwise set to `null`.
        - Extract the experience section first before processing other tables to avoid token loss.
            ### **Important:** Ensure **every experience entry** is captured fully, no matter how fragmented, and no entries are omitted. Return **only** the structured JSON output.
            - **Experience Table:**  It is *absolutely crucial* that *every single* experience entry is extracted, no matter how fragmented or poorly formatted it appears in the resume.  Do not omit any experience entries.  If an entry spans multiple lines, merge those lines to create a complete entry.  Double-check your output against the original resume to ensure no experience details are missing.
    - **Certificate Table:**
        - Extract **all** certificates, **visas**, **passports**, and **flag documents**, even if scattered or multi-line.
        - Merge related certificates into a single entry (e.g., "GMDSS ENDORSEMENT").
        - If details like `NUMBER`, `ISSUING VALIDATION DATE`, or `ISSUING PLACE` are missing, set them to `null`.
        - Include documents like **National Documents** (e.g., "SEAFARER’S ID", "TRAVELLING PASSPORT "), **LICENCE** (e.g., "National License (COC)", "GMDSS "), **FLAG DOCUMENTS** (e.g., "Liberian"), **MEDICAL DOCUMENTS** (e.g., "Yellow Fever") in this section. Don't omit any of these documents.
        - If a certificate's NUMBER is **N/A**, do not include that certificate entry in the extracted JSON output; if the NUMBER is missing or empty, it can be included with null as the value.
        - **Certificate Table:**  Ensure that *all* certificates, visas, passports, and flag documents are extracted.  Pay close attention to certificates that might be spread across multiple lines or sections of the resume.  Do not miss any certificates.  If a certificate's details (number, issuing date, place) are missing, use `null` for those fields, but *do not omit the certificate entry itself*.
    3. **Ensuring Accuracy & Completeness:**
    - Scan the entire resume to ensure **no omissions** in `certificate_table`.
    - Maintain original sequence—do not alter entry order.
    - Do **not** include irrelevant text, extra fields, or unrelated details.
    - If data is missing, return `null` but keep the field in the output.
    4. **Output Formatting:**
    - Generate **only** a properly structured JSON response (no extra text, explanations, or code blocks).
    - The JSON must be **clean, well-formatted, and validated** before returning.
    Strictly follow these instructions to ensure 100% accuracy in extraction. Return **only** the structured JSON output.
    """ 
    


    client = OpenAI(api_key=os.getenv('api_key'))

    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": "You are an AI trained to return only valid JSON responses."},
            {"role": "system", "content": prompt},
            {"role": "user", "content": markdown_text}
        ],
        response_format={"type": "json_object"},
        temperature=0
    )

    res_json =  json.loads(response.choices[0].message.content)


    def replace_values(data, mapping):
        if isinstance(data, dict):
            return {mapping.get(key, key): replace_values(value, mapping) for key, value in data.items()}
        elif isinstance(data, list):
            return [replace_values(item, mapping) for item in data]
        elif isinstance(data, str):
            return mapping.get(data, data)  # Replace if found, else keep original
        return data

    mapped_res = replace_values(res_json,mapping_dict)

    return mapped_res
    

    
        


    
  

    
