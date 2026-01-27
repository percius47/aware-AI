import openai
import json
import os
from app.core.config import settings
from typing import List, Dict
from datetime import datetime

class FineTuningService:
    def __init__(self):
        self.client = openai.OpenAI(api_key=settings.OPENAI_API_KEY)
        self.data_dir = settings.FINE_TUNING_DATA_DIR
        os.makedirs(self.data_dir, exist_ok=True)
    
    async def prepare_training_data(
        self,
        conversations: List[Dict[str, str]],
        output_filename: str = None
    ) -> str:
        """Prepare training data in OpenAI format"""
        if not output_filename:
            output_filename = f"training_data_{datetime.now().strftime('%Y%m%d_%H%M%S')}.jsonl"
        
        filepath = os.path.join(self.data_dir, output_filename)
        
        training_data = []
        for conv in conversations:
            # Format as OpenAI fine-tuning format
            messages = []
            if "system" in conv:
                messages.append({"role": "system", "content": conv["system"]})
            messages.append({"role": "user", "content": conv["user"]})
            messages.append({"role": "assistant", "content": conv["assistant"]})
            
            training_data.append({
                "messages": messages
            })
        
        # Write JSONL file
        with open(filepath, 'w') as f:
            for item in training_data:
                f.write(json.dumps(item) + '\n')
        
        return filepath
    
    async def upload_training_file(self, filepath: str) -> str:
        """Upload training file to OpenAI"""
        with open(filepath, 'rb') as f:
            file = self.client.files.create(
                file=f,
                purpose='fine-tune'
            )
        return file.id
    
    async def create_fine_tuning_job(
        self,
        training_file_id: str,
        model: str = "gpt-3.5-turbo",
        suffix: str = None
    ) -> Dict:
        """Create fine-tuning job"""
        job = self.client.fine_tuning.jobs.create(
            training_file=training_file_id,
            model=model,
            suffix=suffix or f"aware-ai-{datetime.now().strftime('%Y%m%d')}"
        )
        return {
            "job_id": job.id,
            "status": job.status,
            "model": job.model
        }
    
    async def get_fine_tuning_status(self, job_id: str) -> Dict:
        """Get fine-tuning job status"""
        job = self.client.fine_tuning.jobs.retrieve(job_id)
        return {
            "job_id": job.id,
            "status": job.status,
            "model": job.fine_tuned_model,
            "trained_tokens": job.trained_tokens
        }
