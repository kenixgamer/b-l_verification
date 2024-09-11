import streamlit as st
import pdfplumber
from langchain_community.document_loaders import Docx2txtLoader, UnstructuredExcelLoader
import tempfile
from langchain_core.prompts import ChatPromptTemplate
from langchain_groq import ChatGroq
from langchain_community.vectorstores import FAISS
from langchain_community.document_loaders import PyPDFLoader
import openpyxl
from langchain.prompts import PromptTemplate
from langchain.chains import create_retrieval_chain
from langchain_community.document_loaders import WebBaseLoader
from langchain.chains.combine_documents import create_stuff_documents_chain
from langchain_core.prompts import MessagesPlaceholder
import pandas as pd
import io
import base64
import os
import datetime
import shutil
import tempfile
import io
import pdfplumber
import openpyxl

# Function to load SVG file and return Base64 encoded string
def load_svg_base64(svg_file_path):
    with open(svg_file_path, "r") as file:
        svg_data = file.read()
    return base64.b64encode(svg_data.encode()).decode()

# API keys
api_keys = ["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",
            "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"]

# Function to check login credentials
def check_login(username, password):
    return username == "admin" and password == "admin"

# Initialize session state
if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False

# Login form
if not st.session_state.logged_in:
    st.markdown("""
        <style>
            .heading {
                font-size: 48px;
                font-weight: bold;
                color: #FFFFFF;
                text-align: center;
                padding: 20px;
                border-radius: 10px;
                box-shadow: 0 4px 8px rgba(0, 0, 0, 0.2);
            }
        </style>
        <div class="heading">
            Login
        </div>
        """, unsafe_allow_html=True)
    
    username = st.text_input("Username")
    password = st.text_input("Password", type="password")
    
    if st.button("Login"):
        if check_login(username, password):
            st.session_state.logged_in = True
            st.rerun()
        else:
            st.error("Invalid username or password")
else:
    # Main application code
    # Base64 encode your SVG file
    svg_base64 = load_svg_base64("TuskerAI Logo.svg")

    # Add SVG logo to the top-left corner of the sidebar
    st.sidebar.markdown(
        f"""
        <style>
        .logo {{
            position: fixed;
            top: 10px;
            left: 10px;
            width: 150px;
            height: auto;
        }}
        </style>
        <img src="data:image/svg+xml;base64,{svg_base64}" class="logo" alt="Logo">
        """,
        unsafe_allow_html=True
    )

    st.markdown("""
        <style>
            .heading {
                font-size: 48px;
                font-weight: bold;
                color: #FFFFFF;
                text-align: center;
                padding: 20px;
                border-radius: 10px;
                box-shadow: 0 4px 8px rgba(0, 0, 0, 0.2);
            }
        </style>
        <div class="heading">
            Rushabh Sealink
        </div>
        """, unsafe_allow_html=True)

    st.markdown("""
        <style>
            .heading {
                font-size: 48px;
                font-weight: bold;
                color: #FFFFFF;
                text-align: center;
                padding: 20px;
                border-radius: 10px;
                box-shadow: 0 4px 8px rgba(0, 0, 0, 0.2);
            }
        </style>
        <div class="heading">
            B/L Verification System
        </div>
        """, unsafe_allow_html=True)

    # Functions to extract text from different file types
    def extract_text_from_pdf(file):
        with pdfplumber.open(file) as pdf:
            return "".join(page.extract_text() for page in pdf.pages)

    def extract_text_from_docx(file):
        with tempfile.NamedTemporaryFile(delete=False) as tmp:
            tmp.write(file.getvalue())
            tmp_path = tmp.name
        loader = Docx2txtLoader(tmp_path)
        return loader.load()

    def extract_text_from_xlsx(file):
        file_content = io.BytesIO(file.getvalue())
        workbook = openpyxl.load_workbook(file_content, data_only=True)
        text = ""
        for sheet in workbook.worksheets:
            for row in sheet.iter_rows(values_only=True):
                row_text = "\t".join(str(cell) if cell is not None else "" for cell in row)
                text += row_text + "\n"
        return text

    # File upload and extraction
    uploaded_file1 = st.sidebar.file_uploader("Upload the Reference File", type=["pdf", "docx", "xlsx"], key="file1")
    uploaded_file2 = st.sidebar.file_uploader("Upload the Draft file", type=["pdf", "docx", "xlsx"], key="file2")

    if uploaded_file1 and uploaded_file2 and st.sidebar.button("Compare"):
        def get_file_text(file, file_type):
            if file_type == "pdf":
                return extract_text_from_pdf(file)
            elif file_type == "docx":
                return extract_text_from_docx(file)
            elif file_type == "xlsx":
                return extract_text_from_xlsx(file)
            else:
                st.write("Unsupported file type")
                return ""

        # Create a unique subfolder in 'Test-Shipment/verification_history'
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        base_folder = "Test-Shipment/verification_history"
        new_folder = os.path.join(base_folder, timestamp)
        os.makedirs(new_folder, exist_ok=True)
        
        # Save the uploaded files to the new subfolder
        file1_path = os.path.join(new_folder, uploaded_file1.name)
        file2_path = os.path.join(new_folder, uploaded_file2.name)
        
        with open(file1_path, "wb") as f:
            f.write(uploaded_file1.getvalue())
        
        with open(file2_path, "wb") as f:
            f.write(uploaded_file2.getvalue())
        
        reference = get_file_text(uploaded_file1, uploaded_file1.name.split('.')[-1])
        draft = get_file_text(uploaded_file2, uploaded_file2.name.split('.')[-1])

        prompt_template = PromptTemplate(
            input_variables=["reference_table", "draft_table"],
            template="""
                    


 system:
                          - type: instructions
                            description: |
                              Given two tables below, one representing the reference document and the other the draft document, compare them field by field.
                              Fill out the comparison table provided below by matching each field from the reference table with the corresponding field from the draft table.
                              Indicate if there's a discrepancy and suggest corrections if needed.Compare the features of two documents side by side and fill in a table. The table should have the following structure:

                              If the discripency is yes but you are not confident enough just add "Need to review" in the suggested correction column.
                              Follow the format of the comparison table exactly as shown below:

                              | Field Name       | Reference Info | Draft Info | Discrepancy Found? | Suggested Correction |
                              |------------------|----------------|------------|---------------------|----------------------|

                              *Reference Table:*
                              {reference_table}

                              *Draft Table:*
                              {draft_table}

                            Complete the comparison table with the information from the above tables.
                            NOTE:Comparison Should be Very Accurate
                            Imortant Note:Don't Compare List Of Items Which Are Not Mentioned In Both Documents

                            Following features/list of items to consider
                                 - SHIPPER
                                 - BROKER / CHA
                                 - CONSIGNEE
                                 - NOTIFY 1
                                 - NOTIFY 2
                                 - NOTIFY 3
                                 - NOTIFY 4
                                 - VESSEL
                                 - PORT OF LOADING
                                 - PORT OF DISCHARGE
                                 - DESTINATION
                                 - MARKS & NOS
                                 - PARTICULARS
                                 - H.S. CODE
                                 - S.Bill No
                                 - INVOICE NO
                                 - TOTAL GROSS WT
                                 - TOTAL NET WT
                                 - CONTAINER NO
                                 - SEAL NO
                                 - GRS WT/KGS
                                 - NO OF BAGS
                                 - GR.WT./MTS
                                 - NET.WT/MTS
                                 - FREIGHT PREPAID
                                 - CARGO IN TRANSIT TO ETHIOPIA
                                 - VESSEL AND VOYAGE NO.
                                 - BOOKING REF. (or) SHIPPER'S REF.
                                 - PLACE OF RECEIPT
                                 - PLACE OF DELIVERY
                                 - PORT OF DISCHARGE AGENT
                                 - SHIPPER'S LOAD, COUNT AND SEALED
                                 - INCOTERM
                                 - SHIPPER DECLARES
                                 - CONTAINER NUMBERS
                                 - SEAL NUMBERS
                                 - DESCRIPTION OF PACKAGES AND GOODS
                                 - GROSS CARGO WEIGHT
                                 - MEASUREMENT
                                 - FREIGHT & CHARGES CURRENCY PREPAID
                                 - FREIGHT & CHARGES
                                 - CARRIER'S RECEIPT
                                 - DECLARED VALUE
                                 - PLACE AND DATE OF ISSUE
                                 - SHIPPED ON BOARD DATE
                                 - MOVEMENT
                                 - TYPE
                                 - QTY
                                 - P.TYPE
                                 - C.WT(KG)
                                 - TRANSIT CLAUSE
                                 - FREIGHT AS ARRANGED
                                 - EXPORTER
                                 - Agent
                                 - Full address of Place of Receipt
                                 - Final Destination
                                 - No.of original bills of Lading
                                 - Transhipment Vessel
                                 - Port of Transhipment
                                 - Number and Kind of Packages
                                 - Net weight (per bag)
                                 - Gross weight (per bag)
                                 - Net weight (Total)
                                 - Gross weight (Total)
                                 - PACKING DATE
                                 - EXPIRY DATE
                                 - PACKING MARK
                                 - IEC CODE
                                 - Buyer's Order & Date
                                 - 14 DAYS FREE TIME DETENTION AT POD
                                 - Total No.of Containers Packages
                                 - Number of Originals
                                 - Remarks
                                 - Size
                                 - BRAND
                                 - PAN
                                 - GST
                                 - TAX ID
                                 - ACID NO
                                 - IP NO
                                 - AGENT SEAL NO
                                 - AGENT ADDRESS
                                 - TOTAL No. of Containers /Packages
                                 - VOL. (CBM)
                                 - Onward Inland Routing / Export Instructions (Which are contracted separately by Merchants entirely for their own account and risk)
                                 - Also Notify
                                 - Point and Country of Origin
                                 - Forwarding Agent or Export Reference
                                 - COMBINED TRANSPORT BILL OF LADING
                                 - Description Rating Prepaid Collect
                                 - Freight Charges, Etc.
                                 - CY/CY SHIPMENT
                                 - GTI (NHAVA SHEVA)
                                 - WIDE ALPHA / 245E
                                 - SHREE KAILASH GRAIN MILLS PVT. LTD.
                                 - 'SHIPPER'S LOAD,STOW,COUNT,SEAL and WEIGHT'
                                 - MTD No
                                 - Registration No
                                 - Multimodal Transport Document
                                 - Place of Acceptance
                                 - Route/Place of Transhipment
                                 - Modes/Means of Transport/Vessel & Voyage
                                 - No of Original MTD Issued
                                 - Kind of packages/description of goods
                                 - Measurement CBM
                                 - Total Numbers of Containers/Packages
                                 - Type of Service
                                 - Authorized Signatory
                                 - COPY NON-NEGOTIABLE
                                 - ALL DESTINATION CHARGES INCLUDING THC/ PHC/ CFS HANDLING/ DEVANNING ETC PAYABLE BY CONSIGNEE AS PER TARIFF
                                 - INV-SEC
                                 - SHIPPING LINE
                                 - TO ORDER
                                 - Number of Bags
                                 - CONTAINER NO.
                                 - SEAL NUMBER
                                 - NET. WEIGHT
                                 - Ocean Vessel
                                 - Pre-carriage by
                                 - Consignee (If *To order * so indicate)
                                 - B/L Number
                                 - No. of Pkgs
                                 - Description of Goods & Packages
                                 - Onward Inland Routing / Export Instructions
                                 - No. of original B/L(s)
                                 - Exchange Rate Payable at Delivery Agent
                                 - Description Rating Prepaid Collect
                                 - Freight Charges, Etc.
                                 - CY/CY SHIPMENT
                                 - SHIPPER'S LOAD, STOW, COUNT, WEIGHT & SEAL
                                 - FREIGHT
                                 - SHIPPING BILL NO
                                 - BOOKING No
                                 - SHIPPER
                                 - Carrier
                                 - Carrier’s Reference
                                 - Page
                                 - Export References
                                 - Forwarding Agent
                                 - Consignee’s Reference
                                 - Charge Rate Basis Wt/Vol/Val
                                 - Total Freight Prepaid
                                 - Total Freight Collect
                                 - Total Freight
                                 - Freight payable at

                                  Note: Ensure the comparison is highly accurate and comapre all features/list of items and strictly based on the content of the two provided documents. Do not generate content yourself.                    
                                         Imortant Note:Don't Compare List Of Items Which Are Not Mentioned In Both Documents""")
        
        # Format prompt
        prompt = prompt_template.format(reference_table=reference, draft_table=draft)

        def invoke_chat(prompt, api_keys):
            total_keys = len(api_keys)
            for _ in range(total_keys):
                api_key = api_keys.pop(0)  # Take the first API key
                chat = ChatGroq(temperature=0, model="llama-3.1-70b-versatile", api_key=api_key)
                try:
                    response = chat.invoke(prompt)
                    email_template = PromptTemplate(
                        input_variables=["response"],
                        template="Verification results: \n{response}\nYou are the email drafter who has to communicate the changes in verification results if any; in this you must follow now read and should read format."
                    )
                    email_prompt = email_template.format(response=response)
                    email_response = chat.invoke(email_prompt)
                    return response, email_response
                except Exception:
                    api_keys.append(api_key)  # Move the failed API key to the end of the list
            raise Exception("All API keys failed.")

        try:
            response, email_response = invoke_chat(prompt, api_keys)
            st.write(response.content)
            st.markdown(
                """
                <style>
                .centered-heading {
                    text-align: center;
                    font-size: 36px;
                    font-weight: bold;
                }
                </style>
                <div class="centered-heading">EMAIL</div>
                """, unsafe_allow_html=True)
            st.write(email_response.content)
        except Exception as e:
            st.write(f"Failed to get response: {e}")
    else:
        st.markdown("""
        <div style="font-size: 18px; font-weight: bold; color: #FFD700; text-align: center; padding: 20px; border-radius: 10px; background-color: #2E2E2E; box-shadow: 0 4px 8px rgba(0, 0, 0, 0.3);">
            Please upload both the reference and draft PDF files.
        </div>
        """, unsafe_allow_html=True)

    st.markdown("""
        <style>
            .footer {
                position: fixed;
                bottom: 0;
                right: 0;
                width: 100%;
                text-align: right;
                color: #ffffff;
                padding: 10px;
                font-size: 20px;
                font-family: Arial, sans-serif;
            }
        </style>
        <div class="footer">
            Powered by <b>Tusker AI</b>
        </div>
    """, unsafe_allow_html=True)

    # Logout button
    if st.sidebar.button("Logout"):
        st.session_state.logged_in = False
        st.rerun()
