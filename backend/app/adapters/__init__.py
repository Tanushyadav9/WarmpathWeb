"""
backend/app/adapters - External service integration adapters.
"""
from app.adapters.github import get_github_adapter, GitHubProofData

__all__ = ["get_github_adapter", "GitHubProofData"]
