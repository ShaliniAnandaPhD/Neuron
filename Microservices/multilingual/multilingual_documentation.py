from typing import Dict, Any, List, Optional
import json
import uuid

from neuron.agent import DeliberativeAgent, CoordinatorAgent
from neuron.circuit_designer import CircuitDefinition
from neuron.memory import Memory, MemoryType
from neuron.types import AgentType, ConnectionType
from ..base_microservice import BaseMicroservice

class TerminologyAgent(DeliberativeAgent):
    """Agent for managing industry-specific terminology."""
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.terminology_db = {}
        self.load_terminology_database()
    
    def load_terminology_database(self):
        """Load terminology database from storage."""
        # In a real implementation, this would load from a database
        # For now, we'll use a simple dictionary as placeholder
        self.terminology_db = {
            "en": {
                "adaptive resonance": {
                    "definition": "A neural network architecture that self-organizes stable pattern recognition",
                    "domain": "artificial_intelligence",
                    "alternatives": ["ART", "adaptive resonance theory"]
                },
                # More terms would be defined here
            },
            "ja": {
                "adaptive resonance": {
                    "translation": "適応共鳴",
                    "notes": "Technical term with no direct equivalent, may require explanation",
                    "alternatives": ["適応的共鳴理論", "ART"]
                },
                # More terms would be defined here
            },
            # More languages would be defined here
        }
    
    async def process_message(self, message):
        content = message.content
        source_language = content.get("source_language", "en")
        target_language = content.get("target_language", "en")
        document = content.get("document", "")
        
        # Extract terms from the document
        extracted_terms = await self._extract_terms(document, source_language)
        
        # Find translations and alternatives for each term
        translated_terms = await self._translate_terms(extracted_terms, source_language, target_language)
        
        # Create terminology mapping for this document
        terminology_mapping = {
            "source_language": source_language,
            "target_language": target_language,
            "terminology_map": translated_terms,
            "untranslatable_terms": [t for t in extracted_terms if t not in translated_terms],
            "document": document
        }
        
        # Forward to the next agent
        await self.send_message(
            recipients=[message.metadata.get("next_agent", "cultural_adaptation_agent")],
            content=terminology_mapping
        )
    
    async def _extract_terms(self, document, language):
        """Extract industry-specific terms from the document."""
        # In a real implementation, this would use NLP techniques
        # For now, we'll use a simple approach
        
        # Get all terms in our database for this language
        all_terms = self.terminology_db.get(language, {}).keys()
        
        # Check which terms appear in the document
        extracted_terms = []
        for term in all_terms:
            if term.lower() in document.lower():
                extracted_terms.append(term)
                
        # Add detection for alternative forms
        for term, data in self.terminology_db.get(language, {}).items():
            for alt in data.get("alternatives", []):
                if alt.lower() in document.lower() and term not in extracted_terms:
                    extracted_terms.append(term)
        
        return extracted_terms
    
    async def _translate_terms(self, terms, source_language, target_language):
        """Translate terms from source to target language."""
        translated_terms = {}
        
        for term in terms:
            # Check if term exists in source language
            if term in self.terminology_db.get(source_language, {}):
                source_data = self.terminology_db[source_language][term]
                
                # Check if term has translation in target language
                if term in self.terminology_db.get(target_language, {}):
                    target_data = self.terminology_db[target_language][term]
                    translated_terms[term] = {
                        "source": term,
                        "target": target_data.get("translation", term),
                        "definition": source_data.get("definition", ""),
                        "notes": target_data.get("notes", ""),
                        "confidence": 0.9 if "translation" in target_data else 0.5
                    }
                else:
                    # Term exists in source but not in target
                    translated_terms[term] = {
                        "source": term,
                        "target": term,  # Keep original as fallback
                        "definition": source_data.get("definition", ""),
                        "notes": "No direct translation available",
                        "confidence": 0.1
                    }
        
        return translated_terms


class CulturalAdaptationAgent(DeliberativeAgent):
    """Agent for adapting content to target cultures."""
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.cultural_patterns = {}
        self.load_cultural_patterns()
    
    def load_cultural_patterns(self):
        """Load cultural adaptation patterns."""
        # In a real implementation, this would load from a database
        # For now, we'll use a simple dictionary as placeholder
        self.cultural_patterns = {
            "en_US": {
                "date_format": "MM/DD/YYYY",
                "measurement": "imperial",
                "formality": "medium",
                "address_patterns": ["direct", "active_voice"],
                "safety_emphasis": "high",
                "regulatory_references": ["FDA", "OSHA"]
            },
            "ja_JP": {
                "date_format": "YYYY年MM月DD日",
                "measurement": "metric",
                "formality": "high",
                "address_patterns": ["indirect", "passive_voice"],
                "safety_emphasis": "very_high",
                "regulatory_references": ["PMDA", "MHLW"]
            },
            # More regions would be defined here
        }
    
    async def process_message(self, message):
        content = message.content
        source_culture = content.get("source_language", "en_US")
        target_culture = content.get("target_language", "en_US")
        document = content.get("document", "")
        terminology_map = content.get("terminology_map", {})
        
        # Get cultural patterns for source and target
        source_patterns = self.cultural_patterns.get(source_culture, {})
        target_patterns = self.cultural_patterns.get(target_culture, {})
        
        # Identify adaptation needs
        adaptation_needs = await self._identify_adaptation_needs(document, source_patterns, target_patterns)
        
        # Apply cultural adaptations
        adapted_document = await self._apply_adaptations(document, adaptation_needs, terminology_map)
        
        # Create cultural adaptation mapping
        cultural_adaptation = {
            "source_culture": source_culture,
            "target_culture": target_culture,
            "adaptation_patterns_applied": adaptation_needs,
            "original_document": document,
            "adapted_document": adapted_document,
            "terminology_map": terminology_map
        }
        
        # Forward to the next agent
        await self.send_message(
            recipients=[message.metadata.get("next_agent", "format_preservation_agent")],
            content=cultural_adaptation
        )
    
    async def _identify_adaptation_needs(self, document, source_patterns, target_patterns):
        """Identify needed cultural adaptations."""
        adaptation_needs = {}
        
        # Compare patterns between source and target
        for key in source_patterns:
            if key in target_patterns and source_patterns[key] != target_patterns[key]:
                adaptation_needs[key] = {
                    "from": source_patterns[key],
                    "to": target_patterns[key],
                    "detected_in_document": self._pattern_in_document(key, source_patterns[key], document)
                }
        
        return adaptation_needs
    
    def _pattern_in_document(self, pattern_type, pattern_value, document):
        """Check if a specific pattern appears in the document."""
        # This would be more sophisticated in a real implementation
        
        if pattern_type == "date_format" and pattern_value == "MM/DD/YYYY":
            # Check for US date format (simple check)
            import re
            date_pattern = r"\d{1,2}/\d{1,2}/\d{4}"
            return bool(re.search(date_pattern, document))
        
        elif pattern_type == "measurement" and pattern_value == "imperial":
            # Check for imperial units
            imperial_units = ["inch", "inches", "ft", "feet", "lb", "pounds", "oz", "ounces", "gal", "gallons"]
            return any(unit in document for unit in imperial_units)
        
        # More pattern checks would be implemented here
        
        return False
    
    async def _apply_adaptations(self, document, adaptation_needs, terminology_map):
        """Apply cultural adaptations to the document."""
        adapted_document = document
        
        # Apply each adaptation
        for pattern_type, adaptation in adaptation_needs.items():
            if adaptation["detected_in_document"]:
                if pattern_type == "date_format":
                    adapted_document = self._adapt_date_format(
                        adapted_document, 
                        adaptation["from"], 
                        adaptation["to"]
                    )
                
                elif pattern_type == "measurement":
                    adapted_document = self._adapt_measurement_units(
                        adapted_document, 
                        adaptation["from"], 
                        adaptation["to"]
                    )
                
                elif pattern_type == "formality":
                    adapted_document = self._adapt_formality(
                        adapted_document, 
                        adaptation["from"], 
                        adaptation["to"]
                    )
                
                # More adaptation types would be implemented here
        
        # Apply terminology mapping
        for term, mapping in terminology_map.items():
            if mapping["source"] in adapted_document:
                adapted_document = adapted_document.replace(
                    mapping["source"], 
                    mapping["target"]
                )
        
        return adapted_document
    
    def _adapt_date_format(self, document, source_format, target_format):
        """Adapt date formats in the document."""
        # In a real implementation, this would use sophisticated date detection and conversion
        # For now, we'll use a simple placeholder approach
        
        if source_format == "MM/DD/YYYY" and target_format == "YYYY年MM月DD日":
            # Simple regex to find MM/DD/YYYY dates (very basic)
            import re
            date_pattern = r"(\d{1,2})/(\d{1,2})/(\d{4})"
            
            def replace_date(match):
                month, day, year = match.groups()
                return f"{year}年{month}月{day}日"
            
            return re.sub(date_pattern, replace_date, document)
        
        # More format conversions would be implemented here
        
        return document
    
    def _adapt_measurement_units(self, document, source_units, target_units):
        """Adapt measurement units in the document."""
        # In a real implementation, this would use sophisticated unit detection and conversion
        # For now, we'll use a simple placeholder approach
        
        if source_units == "imperial" and target_units == "metric":
            # Convert inches to cm (very basic)
            import re
            inch_pattern = r"(\d+(?:\.\d+)?)\s*(?:inch|inches)"
            
            def replace_inches(match):
                inches = float(match.group(1))
                cm = inches * 2.54
                return f"{cm:.1f} cm"
            
            document = re.sub(inch_pattern, replace_inches, document)
            
            # More unit conversions would be implemented here
        
        return document
    
    def _adapt_formality(self, document, source_formality, target_formality):
        """Adapt the formality level of the document."""
        # This would require sophisticated NLP in a real implementation
        # For now, we'll use a simple placeholder approach
        
        if source_formality == "medium" and target_formality == "high":
            # Simple replacements (very basic)
            informal_phrases = {
                "you should": "it is recommended to",
                "don't": "do not",
                "can't": "cannot",
                # More phrases would be listed here
            }
            
            for informal, formal in informal_phrases.items():
                document = document.replace(informal, formal)
        
        return document


class FormatPreservationAgent(DeliberativeAgent):
    """Agent for preserving document structure and formatting."""
    
    async def process_message(self, message):
        content = message.content
        original_document = content.get("original_document", "")
        adapted_document = content.get("adapted_document", "")
        
        # Extract document structure
        document_structure = await self._extract_document_structure(original_document)
        
        # Apply structure preservation
        formatted_document = await self._preserve_structure(adapted_document, document_structure)
        
        # Create format preservation result
        format_preservation = {
            **content,
            "document_structure": document_structure,
            "formatted_document": formatted_document
        }
        
        # Forward to the next agent
        await self.send_message(
            recipients=[message.metadata.get("next_agent", "safety_critical_content_agent")],
            content=format_preservation
        )
    
    async def _extract_document_structure(self, document):
        """Extract structural elements from the document."""
        # In a real implementation, this would use document parsing
        # For now, we'll use a simple approach
        
        structure = {
            "sections": [],
            "lists": [],
            "tables": [],
            "images": [],
            "formatting": []
        }
        
        # Extract sections (headers)
        import re
        section_pattern = r"(#{1,6})\s+(.+)$"
        for line in document.split("\n"):
            match = re.match(section_pattern, line)
            if match:
                level, title = match.groups()
                structure["sections"].append({
                    "level": len(level),
                    "title": title,
                    "line": document.split("\n").index(line)
                })
        
        # Extract lists (simple detection)
        list_pattern = r"^\s*([*\-+]|\d+\.)\s+(.+)$"
        current_list = None
        
        for i, line in enumerate(document.split("\n")):
            match = re.match(list_pattern, line)
            if match:
                marker, content = match.groups()
                list_type = "ordered" if marker[0].isdigit() else "unordered"
                
                if current_list and current_list["type"] == list_type:
                    current_list["items"].append({
                        "marker": marker,
                        "content": content,
                        "line": i
                    })
                else:
                    if current_list:
                        structure["lists"].append(current_list)
                    
                    current_list = {
                        "type": list_type,
                        "start_line": i,
                        "items": [{
                            "marker": marker,
                            "content": content,
                            "line": i
                        }]
                    }
            elif current_list and line.strip() == "":
                structure["lists"].append(current_list)
                current_list = None
        
        if current_list:
            structure["lists"].append(current_list)
        
        # More structure extraction would be implemented here
        
        return structure
    
    async def _preserve_structure(self, adapted_document, document_structure):
        """Preserve the original document structure in the adapted document."""
        # Split the document into lines for easier manipulation
        lines = adapted_document.split("\n")
        
        # Preserve sections (headers)
        for section in document_structure["sections"]:
            # Make sure the section header follows the correct format
            line_index = min(section["line"], len(lines) - 1)
            line = lines[line_index]
            
            # Check if already a header
            header_match = re.match(r"(#{1,6})\s+(.+)$", line)
            if header_match:
                # Already a header, ensure correct level
                current_level = len(header_match.group(1))
                if current_level != section["level"]:
                    # Fix the header level
                    lines[line_index] = "#" * section["level"] + " " + header_match.group(2)
            else:
                # Not a header, make it one
                lines[line_index] = "#" * section["level"] + " " + line
        
        # Preserve lists
        for list_struct in document_structure["lists"]:
            list_type = list_struct["type"]
            start_line = min(list_struct["start_line"], len(lines) - 1)
            
            for i, item in enumerate(list_struct["items"]):
                line_index = min(item["line"], len(lines) - 1)
                
                # Check if line is already a list item
                list_match = re.match(r"^\s*([*\-+]|\d+\.)\s+(.+)$", lines[line_index])
                if list_match:
                    # Already a list item, ensure correct type
                    current_marker = list_match.group(1)
                    current_type = "ordered" if current_marker[0].isdigit() else "unordered"
                    
                    if current_type != list_type:
                        # Fix the list item type
                        if list_type == "ordered":
                            lines[line_index] = f"{i+1}. {list_match.group(2)}"
                        else:
                            lines[line_index] = f"- {list_match.group(2)}"
                else:
                    # Not a list item, make it one
                    if list_type == "ordered":
                        lines[line_index] = f"{i+1}. {lines[line_index]}"
                    else:
                        lines[line_index] = f"- {lines[line_index]}"
        
        # More structure preservation would be implemented here
        
        return "\n".join(lines)


class SafetyCriticalContentAgent(DeliberativeAgent):
    """Agent for handling safety-critical content with high precision."""
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.safety_patterns = {}
        self.load_safety_patterns()
    
    def load_safety_patterns(self):
        """Load safety-critical content patterns."""
        # In a real implementation, this would load from a database
        # For now, we'll use a simple dictionary as placeholder
        self.safety_patterns = {
            "warning": {
                "en": r"(?i)warning[:\s]+(.*?)(?=\n\n|\Z)",
                "ja": r"(?i)警告[：:\s]+(.*?)(?=\n\n|\Z)",
                # More languages would be defined here
            },
            "caution": {
                "en": r"(?i)caution[:\s]+(.*?)(?=\n\n|\Z)",
                "ja": r"(?i)注意[：:\s]+(.*?)(?=\n\n|\Z)",
                # More languages would be defined here
            },
            "danger": {
                "en": r"(?i)danger[:\s]+(.*?)(?=\n\n|\Z)",
                "ja": r"(?i)危険[：:\s]+(.*?)(?=\n\n|\Z)",
                # More languages would be defined here
            },
            # More safety message types would be defined here
        }
    
    async def process_message(self, message):
        content = message.content
        original_document = content.get("original_document", "")
        formatted_document = content.get("formatted_document", "")
        source_language = content.get("source_language", "en")
        target_language = content.get("target_language", "en")
        
        # Extract safety-critical content
        safety_content = await self._extract_safety_content(original_document, source_language)
        
        # Verify safety content in translated document
        verification_result = await self._verify_safety_content(formatted_document, safety_content, target_language)
        
        # Fix any issues with safety content
        final_document = await self._fix_safety_content(formatted_document, verification_result, target_language)
        
        # Create safety verification result
        safety_verification = {
            **content,
            "safety_content": safety_content,
            "safety_verification": verification_result,
            "final_document": final_document
        }
        
        # Forward to the output agent
        await self.send_message(
            recipients=[message.metadata.get("output_agent", "output")],
            content=safety_verification
        )
    
    async def _extract_safety_content(self, document, language):
        """Extract safety-critical content from the document."""
        safety_content = {}
        
        # Extract each type of safety message
        for message_type, patterns in self.safety_patterns.items():
            if language in patterns:
                pattern = patterns[language]
                
                import re
                matches = re.findall(pattern, document, re.DOTALL)
                
                if matches:
                    safety_content[message_type] = matches
        
        return safety_content
    
    async def _verify_safety_content(self, document, safety_content, language):
        """Verify safety content in the translated document."""
        verification_result = {
            "verified": True,
            "issues": []
        }
        
        # Check each type of safety message
        for message_type, messages in safety_content.items():
            if language in self.safety_patterns[message_type]:
                pattern = self.safety_patterns[message_type][language]
                
                import re
                matches = re.findall(pattern, document, re.DOTALL)
                
                # Verify all original messages are present
                if len(matches) != len(messages):
                    verification_result["verified"] = False
                    verification_result["issues"].append({
                        "type": message_type,
                        "issue": "missing_messages",
                        "expected": len(messages),
                        "found": len(matches)
                    })
                
                # More sophisticated verification would be implemented here
        
        return verification_result
    
    async def _fix_safety_content(self, document, verification_result, language):
        """Fix any issues with safety content in the document."""
        if verification_result["verified"]:
            return document
        
        # Fix issues
        fixed_document = document
        
        for issue in verification_result["issues"]:
            if issue["issue"] == "missing_messages":
                # This would need to be much more sophisticated in a real implementation
                # For now, we'll add a note about the missing safety information
                
                fixed_document += f"\n\n[NOTE: This document is missing {issue['expected'] - issue['found']} " \
                                 f"{issue['type']} messages that were present in the original document. " \
                                 f"Please review the translation for completeness.]"
        
        return fixed_document


class OutputAgent(DeliberativeAgent):
    """Agent for finalizing and returning the translated document."""
    
    async def process_message(self, message):
        content = message.content
        final_document = content.get("final_document", "")
        
        # Create final output
        output = {
            "document_id": str(uuid.uuid4()),
            "source_language": content.get("source_language", "en"),
            "target_language": content.get("target_language", "en"),
            "translated_document": final_document,
            "metadata": {
                "terminology_count": len(content.get("terminology_map", {})),
                "cultural_adaptations": list(content.get("adaptation_patterns_applied", {}).keys()),
                "safety_verified": content.get("safety_verification", {}).get("verified", False),
                "issues": content.get("safety_verification", {}).get("issues", [])
            }
        }
        
        # Return the result
        return output


class MultilingualDocumentationMicroservice(BaseMicroservice):
    """Microservice for multilingual documentation processing."""
    
    def _initialize(self):
        """Initialize the multilingual documentation agents."""
        self.agents = {
            "terminology": TerminologyAgent(name="Terminology Agent"),
            "cultural_adaptation": CulturalAdaptationAgent(name="Cultural Adaptation Agent"),
            "format_preservation": FormatPreservationAgent(name="Format Preservation Agent"),
            "safety_critical_content": SafetyCriticalContentAgent(name="Safety-Critical Content Agent"),
            "output": OutputAgent(name="Output Agent")
        }
    
    def get_circuit_definition(self):
        """Get the circuit definition for multilingual documentation."""
        return CircuitDefinition.create(
            name=f"{self.name} Circuit",
            description=self.description or "Multilingual documentation processing pipeline",
            agents={
                "terminology": {
                    "type": "TerminologyAgent",
                    "instance": self.agents["terminology"]
                },
                "cultural_adaptation": {
                    "type": "CulturalAdaptationAgent",
                    "instance": self.agents["cultural_adaptation"]
                },
                "format_preservation": {
                    "type": "FormatPreservationAgent",
                    "instance": self.agents["format_preservation"]
                },
                "safety_critical_content": {
                    "type": "SafetyCriticalContentAgent",
                    "instance": self.agents["safety_critical_content"]
                },
                "output": {
                    "type": "OutputAgent",
                    "instance": self.agents["output"]
                }
            },
            connections=[
                {
                    "source": "terminology",
                    "target": "cultural_adaptation",
                    "connection_type": ConnectionType.DIRECT
                },
                {
                    "source": "cultural_adaptation",
                    "target": "format_preservation",
                    "connection_type": ConnectionType.DIRECT
                },
                {
                    "source": "format_preservation",
                    "target": "safety_critical_content",
                    "connection_type": ConnectionType.DIRECT
                },
                {
                    "source": "safety_critical_content",
                    "target": "output",
                    "connection_type": ConnectionType.DIRECT
                }
            ],
            input_agents=["terminology"],
            output_agents=["output"]
        )
    
    async def translate_document(self, document, source_language, target_language):
        """Translate a document from source to target language."""
        input_data = {
            "document": document,
            "source_language": source_language,
            "target_language": target_language
        }
        return await self.process(input_data)
