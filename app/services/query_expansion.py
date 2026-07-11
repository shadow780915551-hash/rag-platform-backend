"""
Query Expansion Service Module

This module handles query expansion for improved search recall.
"""

from typing import List, Set
import re
from nltk.corpus import wordnet
from nltk.tokenize import word_tokenize
from nltk.stem import WordNetLemmatizer
from loguru import logger

# Initialize NLTK components
lemmatizer = WordNetLemmatizer()


class QueryExpansionService:
    """
    Service for expanding search queries to improve recall.
    
    This service provides methods to expand queries using synonyms,
    lemmatization, and other NLP techniques.
    """
    
    def __init__(self):
        """
        Initialize the query expansion service.
        """
        self.stop_words = self._load_stop_words()
        logger.info("Query expansion service initialized")
    
    def _load_stop_words(self) -> Set[str]:
        """
        Load common stop words.
        
        Returns:
            Set[str]: Set of stop words
        """
        try:
            from nltk.corpus import stopwords
            return set(stopwords.words('english'))
        except:
            # Fallback if NLTK data not downloaded
            return {
                'a', 'an', 'the', 'and', 'or', 'but', 'in', 'on', 'at', 'to',
                'for', 'of', 'with', 'by', 'from', 'as', 'is', 'was', 'are',
                'were', 'be', 'been', 'being', 'have', 'has', 'had', 'do', 'does',
                'did', 'will', 'would', 'could', 'should', 'may', 'might', 'must'
            }
    
    def expand_with_synonyms(self, query: str, max_synonyms: int = 2) -> List[str]:
        """
        Expand query using WordNet synonyms.
        
        Args:
            query: Original query
            max_synonyms: Maximum number of synonyms per word
            
        Returns:
            List[str]: List of expanded queries
        """
        expanded_queries = [query]
        
        try:
            # Tokenize query
            tokens = word_tokenize(query.lower())
            
            # Get synonyms for each token
            for i, token in enumerate(tokens):
                if token in self.stop_words:
                    continue
                
                # Get synonyms from WordNet
                synsets = wordnet.synsets(token)
                synonyms = set()
                
                for synset in synsets[:max_synonyms]:
                    for lemma in synset.lemmas():
                        synonym = lemma.name().replace('_', ' ')
                        if synonym != token and synonym not in self.stop_words:
                            synonyms.add(synonym)
                
                # Create expanded queries with synonyms
                for synonym in list(synonyms)[:max_synonyms]:
                    expanded_tokens = tokens.copy()
                    expanded_tokens[i] = synonym
                    expanded_query = ' '.join(expanded_tokens)
                    expanded_queries.append(expanded_query)
        
        except Exception as e:
            logger.warning(f"Failed to expand query with synonyms: {e}")
        
        return expanded_queries
    
    def expand_with_lemmatization(self, query: str) -> str:
        """
        Expand query using lemmatization.
        
        Args:
            query: Original query
            
        Returns:
            str: Lemmatized query
        """
        try:
            tokens = word_tokenize(query.lower())
            lemmatized_tokens = [lemmatizer.lemmatize(token) for token in tokens]
            return ' '.join(lemmatized_tokens)
        except Exception as e:
            logger.warning(f"Failed to lemmatize query: {e}")
            return query
    
    def expand_with_variations(self, query: str) -> List[str]:
        """
        Expand query with common variations.
        
        Args:
            query: Original query
            
        Returns:
            List[str]: List of query variations
        """
        variations = [query]
        
        # Add query with and without common articles
        query_lower = query.lower()
        
        # Remove articles
        no_articles = re.sub(r'\b(a|an|the)\b', '', query_lower)
        no_articles = ' '.join(no_articles.split())
        if no_articles != query_lower:
            variations.append(no_articles)
        
        # Add plural/singular variations
        tokens = word_tokenize(query_lower)
        for i, token in enumerate(tokens):
            if token.endswith('s'):
                singular = token[:-1]
                if singular in self.stop_words:
                    continue
                varied_tokens = tokens.copy()
                varied_tokens[i] = singular
                variations.append(' '.join(varied_tokens))
            else:
                plural = token + 's'
                varied_tokens = tokens.copy()
                varied_tokens[i] = plural
                variations.append(' '.join(varied_tokens))
        
        return list(set(variations))
    
    def expand_query(self, query: str, use_synonyms: bool = True, use_lemmatization: bool = True) -> List[str]:
        """
        Expand query using multiple techniques.
        
        Args:
            query: Original query
            use_synonyms: Whether to use synonym expansion
            use_lemmatization: Whether to use lemmatization
            
        Returns:
            List[str]: List of expanded queries
        """
        expanded_queries = [query]
        
        # Add lemmatized version
        if use_lemmatization:
            lemmatized = self.expand_with_lemmatization(query)
            if lemmatized != query:
                expanded_queries.append(lemmatized)
        
        # Add synonym expansions
        if use_synonyms:
            synonym_expansions = self.expand_with_synonyms(query)
            expanded_queries.extend(synonym_expansions)
        
        # Add variations
        variations = self.expand_with_variations(query)
        expanded_queries.extend(variations)
        
        # Remove duplicates while preserving order
        seen = set()
        unique_queries = []
        for q in expanded_queries:
            if q not in seen:
                seen.add(q)
                unique_queries.append(q)
        
        return unique_queries


# Global query expansion service instance
_query_expansion_service = None


def get_query_expansion_service() -> QueryExpansionService:
    """
    Get or create the global query expansion service instance.
    
    Returns:
        QueryExpansionService: Global query expansion service instance
    """
    global _query_expansion_service
    if _query_expansion_service is None:
        _query_expansion_service = QueryExpansionService()
    return _query_expansion_service
