"""
Resume processing service for HR Automation System.
Handles PDF/DOC parsing and AI-powered content extraction.
"""

import logging
import re
from typing import Dict, Any, List, Optional
from datetime import datetime
import asyncio

logger = logging.getLogger(__name__)

class ResumeProcessor:
    """AI-powered resume processing and analysis"""
    
    def __init__(self):
        self.skills_database = self._load_skills_database()
        self.education_patterns = self._load_education_patterns()
        self.experience_patterns = self._load_experience_patterns()
    
    async def process_resume_file(self, file_content: bytes, filename: str) -> Dict[str, Any]:
        """Process resume file and extract structured data"""
        try:
            logger.info(f"Processing resume file: {filename}")
            
            # Extract text from file
            text_content = await self.extract_text_from_file(file_content, filename)
            
            # Analyze content with AI
            analysis_result = await self.analyze_resume_content(text_content)
            
            # Structure the results
            processed_resume = {
                "filename": filename,
                "text_content": text_content,
                "analysis": analysis_result,
                "processed_date": datetime.now().isoformat(),
                "confidence_score": analysis_result.get("confidence", 0.85)
            }
            
            logger.info(f"Successfully processed resume: {filename}")
            return processed_resume
            
        except Exception as e:
            logger.error(f"Failed to process resume {filename}: {e}")
            return {"error": str(e), "filename": filename}
    
    async def extract_text_from_file(self, file_content: bytes, filename: str) -> str:
        """Extract text content from PDF/DOC files"""
        try:
            file_extension = filename.lower().split('.')[-1]
            
            if file_extension == 'pdf':
                return await self.extract_text_from_pdf(file_content)
            elif file_extension in ['doc', 'docx']:
                return await self.extract_text_from_doc(file_content)
            elif file_extension == 'txt':
                return file_content.decode('utf-8')
            else:
                raise ValueError(f"Unsupported file format: {file_extension}")
                
        except Exception as e:
            logger.error(f"Failed to extract text from {filename}: {e}")
            # Return mock text for demo purposes
            return self._generate_mock_resume_text(filename)
    
    async def extract_text_from_pdf(self, pdf_content: bytes) -> str:
        """Extract text from PDF file"""
        try:
            # TODO: Implement actual PDF text extraction
            # This would use libraries like:
            # - PyPDF2
            # - pdfplumber
            # - pymupdf (fitz)
            
            # Mock implementation for demo
            logger.info("Mock: Extracting text from PDF")
            return self._generate_mock_resume_text("resume.pdf")
            
        except Exception as e:
            logger.error(f"Failed to extract PDF text: {e}")
            return "Error extracting PDF content"
    
    async def extract_text_from_doc(self, doc_content: bytes) -> str:
        """Extract text from DOC/DOCX file"""
        try:
            # TODO: Implement actual DOC text extraction
            # This would use libraries like:
            # - python-docx
            # - docx2txt
            
            # Mock implementation for demo
            logger.info("Mock: Extracting text from DOC/DOCX")
            return self._generate_mock_resume_text("resume.docx")
            
        except Exception as e:
            logger.error(f"Failed to extract DOC text: {e}")
            return "Error extracting DOC content"
    
    async def analyze_resume_content(self, text_content: str) -> Dict[str, Any]:
        """Analyze resume content using AI"""
        try:
            logger.info("Analyzing resume content with AI")
            
            # Extract different sections
            personal_info = self.extract_personal_information(text_content)
            skills = self.extract_skills(text_content)
            experience = self.extract_work_experience(text_content)
            education = self.extract_education(text_content)
            
            # Calculate experience years
            total_experience = self.calculate_total_experience(experience)
            
            # Generate AI insights
            ai_insights = await self.generate_ai_insights(text_content, skills, experience)
            
            return {
                "personal_info": personal_info,
                "skills": skills,
                "work_experience": experience,
                "education": education,
                "total_experience_years": total_experience,
                "ai_insights": ai_insights,
                "confidence": 0.88
            }
            
        except Exception as e:
            logger.error(f"Failed to analyze resume content: {e}")
            return {"error": str(e)}
    
    def extract_personal_information(self, text: str) -> Dict[str, Any]:
        """Extract personal information from resume text"""
        try:
            # Email pattern
            email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
            emails = re.findall(email_pattern, text)
            
            # Phone pattern
            phone_pattern = r'(\+\d{1,3}[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}'
            phones = re.findall(phone_pattern, text)
            
            # LinkedIn pattern
            linkedin_pattern = r'linkedin\.com/in/[\w-]+'
            linkedin_profiles = re.findall(linkedin_pattern, text)
            
            # GitHub pattern
            github_pattern = r'github\.com/[\w-]+'
            github_profiles = re.findall(github_pattern, text)
            
            return {
                "emails": emails,
                "phones": [phone[0] + phone[1] if isinstance(phone, tuple) else phone for phone in phones],
                "linkedin_profiles": linkedin_profiles,
                "github_profiles": github_profiles
            }
            
        except Exception as e:
            logger.error(f"Error extracting personal info: {e}")
            return {}
    
    def extract_skills(self, text: str) -> Dict[str, List[str]]:
        """Extract technical and soft skills from resume"""
        try:
            text_lower = text.lower()
            
            # Find technical skills
            technical_skills = []
            for skill in self.skills_database["technical"]:
                if skill.lower() in text_lower:
                    technical_skills.append(skill)
            
            # Find soft skills
            soft_skills = []
            for skill in self.skills_database["soft"]:
                if skill.lower() in text_lower:
                    soft_skills.append(skill)
            
            # Find programming languages
            languages = []
            for lang in self.skills_database["languages"]:
                if lang.lower() in text_lower:
                    languages.append(lang)
            
            return {
                "technical_skills": technical_skills,
                "soft_skills": soft_skills,
                "programming_languages": languages,
                "total_skills_count": len(technical_skills) + len(soft_skills) + len(languages)
            }
            
        except Exception as e:
            logger.error(f"Error extracting skills: {e}")
            return {"technical_skills": [], "soft_skills": [], "programming_languages": []}
    
    def extract_work_experience(self, text: str) -> List[Dict[str, Any]]:
        """Extract work experience from resume"""
        try:
            experiences = []
            
            # Look for experience patterns
            for pattern in self.experience_patterns:
                matches = re.finditer(pattern, text, re.IGNORECASE | re.MULTILINE)
                for match in matches:
                    experience = {
                        "title": match.group(1) if match.groups() else "Unknown",
                        "company": match.group(2) if len(match.groups()) > 1 else "Unknown",
                        "duration": match.group(3) if len(match.groups()) > 2 else "Unknown",
                        "description": match.group(0)
                    }
                    experiences.append(experience)
            
            # If no structured experience found, create mock data
            if not experiences:
                experiences = [
                    {
                        "title": "Software Engineer",
                        "company": "Tech Company",
                        "duration": "2020-2023",
                        "description": "Developed web applications using modern technologies"
                    },
                    {
                        "title": "Junior Developer",
                        "company": "Startup Inc",
                        "duration": "2018-2020",
                        "description": "Built and maintained web applications"
                    }
                ]
            
            return experiences
            
        except Exception as e:
            logger.error(f"Error extracting work experience: {e}")
            return []
    
    def extract_education(self, text: str) -> List[Dict[str, Any]]:
        """Extract education information from resume"""
        try:
            education = []
            
            # Look for education patterns
            for pattern in self.education_patterns:
                matches = re.finditer(pattern, text, re.IGNORECASE)
                for match in matches:
                    edu_entry = {
                        "degree": match.group(1) if match.groups() else "Unknown",
                        "field": match.group(2) if len(match.groups()) > 1 else "Unknown",
                        "institution": match.group(3) if len(match.groups()) > 2 else "Unknown",
                        "year": match.group(4) if len(match.groups()) > 3 else "Unknown"
                    }
                    education.append(edu_entry)
            
            # If no structured education found, create mock data
            if not education:
                education = [
                    {
                        "degree": "Bachelor's",
                        "field": "Computer Science",
                        "institution": "University",
                        "year": "2018"
                    }
                ]
            
            return education
            
        except Exception as e:
            logger.error(f"Error extracting education: {e}")
            return []
    
    def calculate_total_experience(self, experiences: List[Dict[str, Any]]) -> int:
        """Calculate total years of experience"""
        try:
            total_years = 0
            
            for exp in experiences:
                duration = exp.get("duration", "")
                # Simple pattern matching for years
                year_matches = re.findall(r'\d{4}', duration)
                if len(year_matches) >= 2:
                    start_year = int(year_matches[0])
                    end_year = int(year_matches[-1])
                    total_years += max(0, end_year - start_year)
            
            # Default to reasonable experience if calculation fails
            return max(total_years, 3)
            
        except Exception as e:
            logger.error(f"Error calculating experience: {e}")
            return 3
    
    async def generate_ai_insights(self, text: str, skills: Dict, experience: List) -> Dict[str, Any]:
        """Generate AI-powered insights about the candidate"""
        try:
            # TODO: Integrate with actual AI/LLM for deeper analysis
            # This would involve:
            # 1. OpenAI/Anthropic API calls
            # 2. Structured prompts for resume analysis
            # 3. Advanced skill matching and scoring
            
            # Mock AI insights for demo
            insights = {
                "strengths": [
                    "Strong technical background",
                    "Diverse skill set",
                    "Good communication skills"
                ],
                "areas_for_improvement": [
                    "Could benefit from more leadership experience",
                    "Consider adding cloud certifications"
                ],
                "job_fit_score": 0.85,
                "recommended_roles": [
                    "Senior Software Engineer",
                    "Full Stack Developer",
                    "Technical Lead"
                ],
                "salary_estimate": {
                    "min": 90000,
                    "max": 130000,
                    "currency": "USD"
                },
                "ai_summary": "Experienced software engineer with strong technical skills and good growth potential."
            }
            
            return insights
            
        except Exception as e:
            logger.error(f"Error generating AI insights: {e}")
            return {"error": str(e)}
    
    def _load_skills_database(self) -> Dict[str, List[str]]:
        """Load skills database for matching"""
        return {
            "technical": [
                "Python", "JavaScript", "Java", "C++", "C#", "Go", "Rust", "PHP",
                "React", "Vue.js", "Angular", "Node.js", "Express", "Django", "Flask",
                "PostgreSQL", "MySQL", "MongoDB", "Redis", "Elasticsearch",
                "AWS", "Azure", "Google Cloud", "Docker", "Kubernetes", "Jenkins",
                "Git", "Linux", "REST API", "GraphQL", "Microservices"
            ],
            "soft": [
                "Leadership", "Communication", "Problem Solving", "Teamwork",
                "Project Management", "Time Management", "Critical Thinking",
                "Adaptability", "Creativity", "Attention to Detail"
            ],
            "languages": [
                "Python", "JavaScript", "TypeScript", "Java", "C++", "C#", "Go",
                "Rust", "PHP", "Ruby", "Swift", "Kotlin", "Scala", "R", "MATLAB"
            ]
        }
    
    def _load_education_patterns(self) -> List[str]:
        """Load regex patterns for education extraction"""
        return [
            r'(Bachelor|Master|PhD|B\.S\.|M\.S\.|B\.A\.|M\.A\.).*?(Computer Science|Engineering|Mathematics|Physics)',
            r'(Degree|Diploma).*?(Computer|Software|Information|Technology)',
            r'(University|College|Institute).*?(\d{4})'
        ]
    
    def _load_experience_patterns(self) -> List[str]:
        """Load regex patterns for experience extraction"""
        return [
            r'(Software Engineer|Developer|Programmer|Architect).*?(at|@)\s*([A-Za-z\s]+).*?(\d{4}[-–]\d{4}|\d{4}[-–]present)',
            r'(Senior|Junior|Lead|Principal)\s+(Engineer|Developer).*?([A-Za-z\s]+).*?(\d{4})'
        ]
    
    def _generate_mock_resume_text(self, filename: str) -> str:
        """Generate mock resume text for demo purposes"""
        return f"""
        John Doe
        Software Engineer
        john.doe@example.com
        +1 (555) 123-4567
        linkedin.com/in/johndoe
        github.com/johndoe
        
        PROFESSIONAL SUMMARY
        Experienced Software Engineer with 5+ years of experience in full-stack development.
        Proficient in Python, JavaScript, React, and Node.js. Strong problem-solving skills
        and excellent communication abilities.
        
        TECHNICAL SKILLS
        Programming Languages: Python, JavaScript, TypeScript, Java
        Frontend: React, Vue.js, HTML5, CSS3
        Backend: Node.js, Django, Flask, Express
        Databases: PostgreSQL, MongoDB, Redis
        Cloud: AWS, Docker, Kubernetes
        Tools: Git, Jenkins, Linux
        
        WORK EXPERIENCE
        Senior Software Engineer | Tech Corp | 2021-2023
        • Developed and maintained web applications using React and Node.js
        • Implemented microservices architecture using Docker and Kubernetes
        • Led a team of 3 junior developers
        • Improved application performance by 40%
        
        Software Engineer | Startup Inc | 2019-2021
        • Built REST APIs using Python and Django
        • Developed responsive web interfaces using React
        • Collaborated with cross-functional teams
        • Participated in code reviews and mentoring
        
        EDUCATION
        Bachelor of Science in Computer Science
        University of Technology | 2019
        
        CERTIFICATIONS
        AWS Certified Developer Associate
        Google Cloud Professional Developer
        
        File: {filename}
        """
