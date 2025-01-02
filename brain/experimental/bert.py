from transformers import pipeline, AutoTokenizer, AutoModelForSequenceClassification
import torch
from typing import List, Dict, Tuple

class Bret:
    def __init__(self, model_id: str = "facebook/bart-large-mnli"):
        """Initialize Bret with BART model for zero-shot topic classification.
        
        Args:
            model_id: HuggingFace model ID to use. Defaults to BART large MNLI.
        """
        self.model_id = model_id
        self.tokenizer = AutoTokenizer.from_pretrained(model_id)
        self.model = AutoModelForSequenceClassification.from_pretrained(model_id)
        self.classifier = pipeline(
            "zero-shot-classification",
            model=model_id,
            tokenizer=self.tokenizer,
            torch_dtype=torch.bfloat16
        )
    
    def classify_topic(self, text: str, candidate_topics: List[str]) -> str:
        """Classify text into most likely topic.
        
        Args:
            text: Input text to classify
            candidate_topics: List of possible topic categories
            
        Returns:
            Most likely topic category
        """
        result = self.classifier(text, candidate_topics)
        return result["labels"][0]

    def get_topic_scores(self, text: str, candidate_topics: List[str]) -> List[Tuple[str, float]]:
        """Get likelihood scores for each candidate topic.
        
        Args:
            text: Input text to classify
            candidate_topics: List of possible topic categories
            
        Returns:
            List of (topic, score) tuples sorted by descending score
        """
        result = self.classifier(text, candidate_topics)
        return list(zip(result["labels"], result["scores"]))

    def test_classification(self):
        """Test topic classification on sample sentences."""
        test_sentences = [
            "The new quantum computer can perform calculations in seconds that would take classical computers years.",
            "The basketball team won their third championship title after an amazing overtime victory.",
            "Scientists discovered a new species of butterfly in the Amazon rainforest.",
            "The stock market saw significant gains today as tech companies reported strong earnings."
        ]
        
        candidate_topics = ["Technology", "Sports", "Science", "Finance"]
        
        print("\nTesting topic classification:")
        print("-" * 50)
        for sentence in test_sentences:
            topic = self.classify_topic(sentence, candidate_topics)
            print(f"\nSentence: {sentence}")
            print(f"Classified as: {topic}")
            
            # Get detailed scores
            scores = self.get_topic_scores(sentence, candidate_topics)
            print("\nDetailed scores:")
            for topic, score in scores:
                print(f"{topic}: {score:.3f}")
