import os
import logging
from dotenv import load_dotenv
import base64
from typing import Dict, Any
from pathlib import Path
from pydantic import BaseModel, Field
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import PydanticOutputParser
from langchain_openai import ChatOpenAI
from langchain_core.exceptions import OutputParserException

load_dotenv()
logger = logging.getLogger(__name__)

class NIDData(BaseModel):
    name: str = Field(description="Full name from the NID card")
    dob: str = Field(description="Date of birth in format DD-MM-YYYY")

def extract_text(image_path: str) -> Dict[str, Any]:
    """
    Extract name and DOB from NID card using LangChain and GPT-4 Vision.
    
    Args:
        image_path: Path to the NID card image
        
    Returns:
        Dict with status, name, and dob
    """
    path = Path(image_path)
    
    if not path.exists():
        logger.error(f"Image not found: {image_path}")
        return {"status": "error", "message": f"Image not found: {image_path}"}

    try:
        parser = PydanticOutputParser(pydantic_object=NIDData)
        
        llm = ChatOpenAI(
            model="gpt-4o",
            temperature=0,
            api_key=os.getenv("OPENAI_API_KEY")
        )
        
        prompt = ChatPromptTemplate.from_messages([
            ("system", "You are an expert at extracting information from government-issued ID cards. "
                      "Always respond with valid JSON in the exact format specified, even if the image quality is poor. "
                      "If you cannot read certain fields clearly, use 'Not readable' as the value but still provide valid JSON."),
            ("user", [
                {"type": "text", "text": "Extract the name and date of birth from this government ID/NID card image. "
                                        "Provide the output in the following JSON format:\n{format_instructions}\n\n"
                                        "Important: You MUST respond with valid JSON only. Do not refuse or explain - just extract what you can see."},
                {"type": "image_url", "image_url": {"url": "data:image/jpeg;base64,{image_data}"}}
            ])
        ])
        
        
        with open(image_path, "rb") as f:
            image_data = base64.b64encode(f.read()).decode()
        
        chain = prompt | llm | parser
        result = chain.invoke({
            "image_data": image_data,
            "format_instructions": parser.get_format_instructions()
        })
        
        logger.info(f"Extraction successful for {image_path}")
        return {
            "status": "success",
            "name": result.name,
            "dob": result.dob
        }
    
    except OutputParserException as e:
        logger.error(f"Parser error - AI may have refused to process: {str(e)}")
        return {
            "status": "error", 
            "message": "Unable to extract data from the image. The image may not be a valid ID card, or the quality may be too poor to read.",
            "details": "AI model refused to process or returned invalid format"
        }
        
    except Exception as e:
        logger.exception(f"Error during extraction: {str(e)}")
        return {"status": "error", "message": f"Error: {str(e)}"}