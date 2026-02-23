"""
Diversity Score Checker - Influencer Script Analysis
Analyzes PDF documents to extract marketing insights: hooks, creative frameworks, and message angles.
Outputs an Excel file with diversity analysis.
"""
import sys
import json
import os
import asyncio
from pathlib import Path
from datetime import datetime
import re

# Load environment variables
from dotenv import load_dotenv
load_dotenv(Path(__file__).parent.parent.parent / '.env')

# Import LLM chat
from emergentintegrations.llm.chat import LlmChat, UserMessage, FileContentWithMimeType

# Excel generation
import pandas as pd
from io import BytesIO

# Hook categories
HOOK_CATEGORIES = [
    "Product Demo Start",
    "Problem/Solution Hook",
    "Testimonial Lead",
    "Before/After Hook",
    "Question Hook",
    "Trend/Challenge Hook",
    "Shocking Statement",
    "Tutorial/How-To Start",
    "UGC Style Opening",
    "Brand Story Hook"
]

# Creative framework categories
FRAMEWORK_CATEGORIES = [
    "Problem-Agitation-Solution (PAS)",
    "Before-After-Bridge (BAB)",
    "Features-Advantages-Benefits (FAB)",
    "AIDA (Attention-Interest-Desire-Action)",
    "Storytelling/Narrative",
    "Testimonial/Review Format",
    "Tutorial/Educational",
    "Day-in-the-Life",
    "Comparison/Versus",
    "Unboxing/First Impressions"
]

# Message angle categories
MESSAGE_ANGLE_CATEGORIES = [
    "Natural/Organic Ingredients",
    "Visible Results/Transformation",
    "Dermatologist/Expert Approved",
    "Value for Money",
    "Gentle/Safe for All Skin Types",
    "Quick/Easy to Use",
    "Long-lasting Effects",
    "Trendy/Must-Have Product",
    "Personal Recommendation",
    "Problem Solver"
]


def build_hook_prompt() -> str:
    """Build the prompt for hook extraction"""
    return f"""You are a performance marketing analyst specializing in video content analysis.

TASK: Analyze the provided PDF document which contains an influencer script/brief. Identify the PRIMARY HOOK used in the first 0-5 seconds of the video script.

HOOK CATEGORIES:
{chr(10).join([f"- {cat}" for cat in HOOK_CATEGORIES])}

OUTPUT FORMAT (JSON only):
{{
    "hook_category": "Category name from the list above",
    "hook_reasoning": "Brief explanation of why this hook category was identified (2-3 sentences max)"
}}

RULES:
1. Only use categories from the provided list
2. Focus on the opening/hook section of the script
3. Be specific and concise in reasoning
4. If no clear hook is identifiable, use "UGC Style Opening" as default
"""


def build_framework_prompt() -> str:
    """Build the prompt for creative framework extraction"""
    return f"""You are a performance marketing analyst specializing in video content analysis.

TASK: Analyze the provided PDF document which contains an influencer script/brief. Identify the PRIMARY CREATIVE FRAMEWORK used in the overall script structure.

CREATIVE FRAMEWORK CATEGORIES:
{chr(10).join([f"- {cat}" for cat in FRAMEWORK_CATEGORIES])}

OUTPUT FORMAT (JSON only):
{{
    "creative_framework": "Framework name from the list above",
    "framework_reasoning": "Brief explanation of why this framework was identified (2-3 sentences max)"
}}

RULES:
1. Only use frameworks from the provided list
2. Analyze the overall structure and flow of the script
3. Be specific and concise in reasoning
4. If no clear framework is identifiable, use "Storytelling/Narrative" as default
"""


def build_message_angle_prompt() -> str:
    """Build the prompt for message angle extraction"""
    return f"""You are a performance marketing analyst specializing in video content analysis.

TASK: Analyze the provided PDF document which contains an influencer script/brief. Identify the PRIMARY MESSAGE ANGLE - the core "reason to buy" or key persuasive argument.

MESSAGE ANGLE CATEGORIES:
{chr(10).join([f"- {cat}" for cat in MESSAGE_ANGLE_CATEGORIES])}

OUTPUT FORMAT (JSON only):
{{
    "message_angle": "Message angle from the list above",
    "message_reasoning": "Brief explanation of why this message angle was identified (2-3 sentences max)"
}}

RULES:
1. Only use message angles from the provided list
2. Focus on the main persuasive argument in the script
3. Be specific and concise in reasoning
4. If no clear message angle is identifiable, use "Personal Recommendation" as default
"""


def clean_json_response(response: str) -> dict:
    """Clean and parse JSON from LLM response"""
    # Remove markdown code fences if present
    cleaned = re.sub(r'^```(?:json)?\s*', '', response.strip())
    cleaned = re.sub(r'\s*```$', '', cleaned)
    
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        # Try to extract JSON object
        match = re.search(r'\{[^{}]*\}', response, re.DOTALL)
        if match:
            return json.loads(match.group())
        raise


async def analyze_document(pdf_path: str, api_key: str) -> dict:
    """Analyze a single document and extract all marketing insights"""
    results = {
        "document_name": Path(pdf_path).stem,
        "hook_category": None,
        "hook_reasoning": None,
        "creative_framework": None,
        "framework_reasoning": None,
        "message_angle": None,
        "message_reasoning": None
    }
    
    # Create file content object for the PDF
    pdf_file = FileContentWithMimeType(
        file_path=pdf_path,
        mime_type="application/pdf"
    )
    
    # Extract Hook
    print(f"  Analyzing hook...")
    hook_chat = LlmChat(
        api_key=api_key,
        session_id=f"hook_{datetime.now().timestamp()}",
        system_message="You are a performance marketing analyst. Respond only with valid JSON."
    ).with_model("gemini", "gemini-2.5-flash")
    
    hook_response = await hook_chat.send_message(UserMessage(
        text=build_hook_prompt(),
        file_contents=[pdf_file]
    ))
    
    try:
        hook_data = clean_json_response(hook_response)
        results["hook_category"] = hook_data.get("hook_category", "UGC Style Opening")
        results["hook_reasoning"] = hook_data.get("hook_reasoning", "")
    except Exception as e:
        print(f"  Warning: Could not parse hook response: {e}")
        results["hook_category"] = "UGC Style Opening"
        results["hook_reasoning"] = "Unable to extract hook information"
    
    # Extract Framework
    print(f"  Analyzing creative framework...")
    framework_chat = LlmChat(
        api_key=api_key,
        session_id=f"framework_{datetime.now().timestamp()}",
        system_message="You are a performance marketing analyst. Respond only with valid JSON."
    ).with_model("gemini", "gemini-2.5-flash")
    
    framework_response = await framework_chat.send_message(UserMessage(
        text=build_framework_prompt(),
        file_contents=[pdf_file]
    ))
    
    try:
        framework_data = clean_json_response(framework_response)
        results["creative_framework"] = framework_data.get("creative_framework", "Storytelling/Narrative")
        results["framework_reasoning"] = framework_data.get("framework_reasoning", "")
    except Exception as e:
        print(f"  Warning: Could not parse framework response: {e}")
        results["creative_framework"] = "Storytelling/Narrative"
        results["framework_reasoning"] = "Unable to extract framework information"
    
    # Extract Message Angle
    print(f"  Analyzing message angle...")
    angle_chat = LlmChat(
        api_key=api_key,
        session_id=f"angle_{datetime.now().timestamp()}",
        system_message="You are a performance marketing analyst. Respond only with valid JSON."
    ).with_model("gemini", "gemini-2.5-flash")
    
    angle_response = await angle_chat.send_message(UserMessage(
        text=build_message_angle_prompt(),
        file_contents=[pdf_file]
    ))
    
    try:
        angle_data = clean_json_response(angle_response)
        results["message_angle"] = angle_data.get("message_angle", "Personal Recommendation")
        results["message_reasoning"] = angle_data.get("message_reasoning", "")
    except Exception as e:
        print(f"  Warning: Could not parse message angle response: {e}")
        results["message_angle"] = "Personal Recommendation"
        results["message_reasoning"] = "Unable to extract message angle information"
    
    return results


def generate_excel_report(results: list, output_path: str) -> str:
    """Generate Excel report with diversity analysis"""
    
    # Create DataFrames
    # 1. Summary DataFrame
    summary_data = {
        "Category": ["Hooks", "Creative Frameworks", "Message Angles"],
        "Total Categories": [len(HOOK_CATEGORIES), len(FRAMEWORK_CATEGORIES), len(MESSAGE_ANGLE_CATEGORIES)],
        "Categories Used": [
            len(set(r["hook_category"] for r in results if r["hook_category"])),
            len(set(r["creative_framework"] for r in results if r["creative_framework"])),
            len(set(r["message_angle"] for r in results if r["message_angle"]))
        ],
        "Documents Analyzed": [len(results)] * 3
    }
    summary_df = pd.DataFrame(summary_data)
    summary_df["Diversity %"] = (summary_df["Categories Used"] / summary_df["Total Categories"] * 100).round(1)
    
    # 2. Detailed Results DataFrame
    detail_df = pd.DataFrame(results)
    detail_df = detail_df[[
        "document_name",
        "hook_category",
        "hook_reasoning",
        "creative_framework",
        "framework_reasoning",
        "message_angle",
        "message_reasoning"
    ]]
    
    # Column name mapping for nicer headers
    detail_df.columns = [
        "Document Name",
        "Hook Category",
        "Hook Reasoning",
        "Creative Framework",
        "Framework Reasoning",
        "Message Angle",
        "Message Reasoning"
    ]
    
    # 3. Categories Reference DataFrame
    max_len = max(len(HOOK_CATEGORIES), len(FRAMEWORK_CATEGORIES), len(MESSAGE_ANGLE_CATEGORIES))
    categories_data = {
        "Hook Categories": HOOK_CATEGORIES + [""] * (max_len - len(HOOK_CATEGORIES)),
        "Framework Categories": FRAMEWORK_CATEGORIES + [""] * (max_len - len(FRAMEWORK_CATEGORIES)),
        "Message Angle Categories": MESSAGE_ANGLE_CATEGORIES + [""] * (max_len - len(MESSAGE_ANGLE_CATEGORIES))
    }
    categories_df = pd.DataFrame(categories_data)
    
    # Write to Excel
    output_file = Path(output_path) / f"Diversity_Analysis_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
    
    with pd.ExcelWriter(output_file, engine='xlsxwriter') as writer:
        # Write sheets
        summary_df.to_excel(writer, sheet_name='Summary', index=False)
        detail_df.to_excel(writer, sheet_name='Detailed Analysis', index=False)
        categories_df.to_excel(writer, sheet_name='Category Reference', index=False)
        
        # Get workbook
        workbook = writer.book
        
        # Format Summary sheet
        summary_sheet = writer.sheets['Summary']
        header_format = workbook.add_format({
            'bold': True,
            'bg_color': '#4472C4',
            'font_color': 'white',
            'border': 1
        })
        
        for col_num, value in enumerate(summary_df.columns.values):
            summary_sheet.write(0, col_num, value, header_format)
        
        summary_sheet.set_column('A:A', 20)
        summary_sheet.set_column('B:E', 18)
        
        # Format Detailed Analysis sheet
        detail_sheet = writer.sheets['Detailed Analysis']
        for col_num, value in enumerate(detail_df.columns.values):
            detail_sheet.write(0, col_num, value, header_format)
        
        detail_sheet.set_column('A:A', 25)
        detail_sheet.set_column('B:B', 22)
        detail_sheet.set_column('C:C', 50)
        detail_sheet.set_column('D:D', 25)
        detail_sheet.set_column('E:E', 50)
        detail_sheet.set_column('F:F', 22)
        detail_sheet.set_column('G:G', 50)
        
        # Format Category Reference sheet
        cat_sheet = writer.sheets['Category Reference']
        for col_num, value in enumerate(categories_df.columns.values):
            cat_sheet.write(0, col_num, value, header_format)
        
        cat_sheet.set_column('A:C', 35)
    
    return str(output_file)


async def main():
    """Main entry point"""
    if len(sys.argv) < 2:
        print("Usage: python main.py <config_json_path>")
        sys.exit(1)
    
    config_path = sys.argv[1]
    
    # Load config
    with open(config_path, 'r') as f:
        config = json.load(f)
    
    print("=" * 60)
    print("DIVERSITY SCORE CHECKER")
    print("=" * 60)
    print(f"Job ID: {config['job_id']}")
    print(f"Files to process: {len(config['files'])}")
    print()
    
    # Get API key
    api_key = os.environ.get('EMERGENT_LLM_KEY')
    if not api_key:
        print("ERROR: EMERGENT_LLM_KEY not found in environment")
        sys.exit(1)
    
    output_path = config.get('output_path', '/tmp')
    
    # Process each file
    results = []
    for file_info in config['files']:
        file_path = file_info.get('local_path')
        filename = file_info.get('filename', Path(file_path).name)
        
        print(f"\nProcessing: {filename}")
        print("-" * 40)
        
        if not file_path or not os.path.exists(file_path):
            print(f"  ERROR: File not found: {file_path}")
            continue
        
        # Check if it's a PDF
        if not filename.lower().endswith('.pdf'):
            print(f"  WARNING: Skipping non-PDF file: {filename}")
            continue
        
        try:
            result = await analyze_document(file_path, api_key)
            results.append(result)
            
            print(f"  Hook: {result['hook_category']}")
            print(f"  Framework: {result['creative_framework']}")
            print(f"  Message Angle: {result['message_angle']}")
            
        except Exception as e:
            print(f"  ERROR: Failed to process file: {str(e)}")
            import traceback
            traceback.print_exc()
    
    print()
    print("=" * 60)
    print("GENERATING REPORT")
    print("=" * 60)
    
    if results:
        output_file = generate_excel_report(results, output_path)
        print(f"\nReport generated: {output_file}")
        print(f"Documents analyzed: {len(results)}")
        
        # Print summary
        print("\n--- DIVERSITY SUMMARY ---")
        unique_hooks = len(set(r["hook_category"] for r in results if r["hook_category"]))
        unique_frameworks = len(set(r["creative_framework"] for r in results if r["creative_framework"]))
        unique_angles = len(set(r["message_angle"] for r in results if r["message_angle"]))
        
        print(f"Unique Hooks: {unique_hooks}/{len(HOOK_CATEGORIES)} ({unique_hooks/len(HOOK_CATEGORIES)*100:.1f}%)")
        print(f"Unique Frameworks: {unique_frameworks}/{len(FRAMEWORK_CATEGORIES)} ({unique_frameworks/len(FRAMEWORK_CATEGORIES)*100:.1f}%)")
        print(f"Unique Message Angles: {unique_angles}/{len(MESSAGE_ANGLE_CATEGORIES)} ({unique_angles/len(MESSAGE_ANGLE_CATEGORIES)*100:.1f}%)")
    else:
        print("No documents were successfully processed.")
        sys.exit(1)
    
    print()
    print("=" * 60)
    print("PROCESSING COMPLETE")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
