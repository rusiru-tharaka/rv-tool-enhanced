"""
Instance Recommendation Service
Maps VM specifications to optimal AWS EC2 instance types
Considers workload patterns, performance requirements, and cost optimization
"""

import logging
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from enum import Enum
import math

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class WorkloadType(str, Enum):
    PRODUCTION = "production"
    DEVELOPMENT = "development"
    TESTING = "testing"
    STAGING = "staging"

class InstanceFamily(str, Enum):
    GENERAL_PURPOSE = "general_purpose"  # M5, M6i
    COMPUTE_OPTIMIZED = "compute_optimized"  # C5, C6i
    MEMORY_OPTIMIZED = "memory_optimized"  # R5, R6i
    BURSTABLE = "burstable"  # T3, T4g

@dataclass
class VMSpecification:
    """VM specification from RVTools data"""
    vm_name: str
    cpu_cores: int
    memory_gb: float
    storage_gb: float
    workload_type: WorkloadType = WorkloadType.PRODUCTION
    os_type: str = "linux"  # linux, windows
    
@dataclass
class InstanceRecommendation:
    """AWS instance recommendation"""
    instance_type: str
    instance_family: InstanceFamily
    vcpu: int
    memory_gb: float
    confidence_score: float  # 0.0 to 1.0
    reasoning: str
    cost_efficiency_score: float  # 0.0 to 1.0
    performance_match_score: float  # 0.0 to 1.0
    alternative_options: List[str] = None

class InstanceRecommendationService:
    """
    Service for recommending optimal AWS EC2 instance types
    Based on VM specifications and workload patterns
    """
    
    def __init__(self):
        # Instance type specifications (vCPU, Memory GB, Network Performance)
        self.instance_specs = {
            # General Purpose - M5 Family
            "m5.large": {"vcpu": 2, "memory": 8, "network": "Up to 10 Gbps", "family": InstanceFamily.GENERAL_PURPOSE},
            "m5.xlarge": {"vcpu": 4, "memory": 16, "network": "Up to 10 Gbps", "family": InstanceFamily.GENERAL_PURPOSE},
            "m5.2xlarge": {"vcpu": 8, "memory": 32, "network": "Up to 10 Gbps", "family": InstanceFamily.GENERAL_PURPOSE},
            "m5.4xlarge": {"vcpu": 16, "memory": 64, "network": "Up to 10 Gbps", "family": InstanceFamily.GENERAL_PURPOSE},
            "m5.8xlarge": {"vcpu": 32, "memory": 128, "network": "10 Gbps", "family": InstanceFamily.GENERAL_PURPOSE},
            "m5.12xlarge": {"vcpu": 48, "memory": 192, "network": "12 Gbps", "family": InstanceFamily.GENERAL_PURPOSE},
            "m5.16xlarge": {"vcpu": 64, "memory": 256, "network": "20 Gbps", "family": InstanceFamily.GENERAL_PURPOSE},
            "m5.24xlarge": {"vcpu": 96, "memory": 384, "network": "25 Gbps", "family": InstanceFamily.GENERAL_PURPOSE},
            
            # General Purpose - M6i Family (newer generation)
            "m6i.large": {"vcpu": 2, "memory": 8, "network": "Up to 12.5 Gbps", "family": InstanceFamily.GENERAL_PURPOSE},
            "m6i.xlarge": {"vcpu": 4, "memory": 16, "network": "Up to 12.5 Gbps", "family": InstanceFamily.GENERAL_PURPOSE},
            "m6i.2xlarge": {"vcpu": 8, "memory": 32, "network": "Up to 12.5 Gbps", "family": InstanceFamily.GENERAL_PURPOSE},
            "m6i.4xlarge": {"vcpu": 16, "memory": 64, "network": "Up to 12.5 Gbps", "family": InstanceFamily.GENERAL_PURPOSE},
            "m6i.8xlarge": {"vcpu": 32, "memory": 128, "network": "12.5 Gbps", "family": InstanceFamily.GENERAL_PURPOSE},
            "m6i.12xlarge": {"vcpu": 48, "memory": 192, "network": "18.75 Gbps", "family": InstanceFamily.GENERAL_PURPOSE},
            "m6i.16xlarge": {"vcpu": 64, "memory": 256, "network": "25 Gbps", "family": InstanceFamily.GENERAL_PURPOSE},
            "m6i.24xlarge": {"vcpu": 96, "memory": 384, "network": "37.5 Gbps", "family": InstanceFamily.GENERAL_PURPOSE},
            
            # Compute Optimized - C5 Family
            "c5.large": {"vcpu": 2, "memory": 4, "network": "Up to 10 Gbps", "family": InstanceFamily.COMPUTE_OPTIMIZED},
            "c5.xlarge": {"vcpu": 4, "memory": 8, "network": "Up to 10 Gbps", "family": InstanceFamily.COMPUTE_OPTIMIZED},
            "c5.2xlarge": {"vcpu": 8, "memory": 16, "network": "Up to 10 Gbps", "family": InstanceFamily.COMPUTE_OPTIMIZED},
            "c5.4xlarge": {"vcpu": 16, "memory": 32, "network": "Up to 10 Gbps", "family": InstanceFamily.COMPUTE_OPTIMIZED},
            "c5.9xlarge": {"vcpu": 36, "memory": 72, "network": "10 Gbps", "family": InstanceFamily.COMPUTE_OPTIMIZED},
            "c5.12xlarge": {"vcpu": 48, "memory": 96, "network": "12 Gbps", "family": InstanceFamily.COMPUTE_OPTIMIZED},
            "c5.18xlarge": {"vcpu": 72, "memory": 144, "network": "25 Gbps", "family": InstanceFamily.COMPUTE_OPTIMIZED},
            "c5.24xlarge": {"vcpu": 96, "memory": 192, "network": "25 Gbps", "family": InstanceFamily.COMPUTE_OPTIMIZED},
            
            # Memory Optimized - R5 Family
            "r5.large": {"vcpu": 2, "memory": 16, "network": "Up to 10 Gbps", "family": InstanceFamily.MEMORY_OPTIMIZED},
            "r5.xlarge": {"vcpu": 4, "memory": 32, "network": "Up to 10 Gbps", "family": InstanceFamily.MEMORY_OPTIMIZED},
            "r5.2xlarge": {"vcpu": 8, "memory": 64, "network": "Up to 10 Gbps", "family": InstanceFamily.MEMORY_OPTIMIZED},
            "r5.4xlarge": {"vcpu": 16, "memory": 128, "network": "Up to 10 Gbps", "family": InstanceFamily.MEMORY_OPTIMIZED},
            "r5.8xlarge": {"vcpu": 32, "memory": 256, "network": "10 Gbps", "family": InstanceFamily.MEMORY_OPTIMIZED},
            "r5.12xlarge": {"vcpu": 48, "memory": 384, "network": "12 Gbps", "family": InstanceFamily.MEMORY_OPTIMIZED},
            "r5.16xlarge": {"vcpu": 64, "memory": 512, "network": "20 Gbps", "family": InstanceFamily.MEMORY_OPTIMIZED},
            "r5.24xlarge": {"vcpu": 96, "memory": 768, "network": "25 Gbps", "family": InstanceFamily.MEMORY_OPTIMIZED},
            
            # Burstable Performance - T3 Family
            "t3.nano": {"vcpu": 2, "memory": 0.5, "network": "Up to 5 Gbps", "family": InstanceFamily.BURSTABLE},
            "t3.micro": {"vcpu": 2, "memory": 1, "network": "Up to 5 Gbps", "family": InstanceFamily.BURSTABLE},
            "t3.small": {"vcpu": 2, "memory": 2, "network": "Up to 5 Gbps", "family": InstanceFamily.BURSTABLE},
            "t3.medium": {"vcpu": 2, "memory": 4, "network": "Up to 5 Gbps", "family": InstanceFamily.BURSTABLE},
            "t3.large": {"vcpu": 2, "memory": 8, "network": "Up to 5 Gbps", "family": InstanceFamily.BURSTABLE},
            "t3.xlarge": {"vcpu": 4, "memory": 16, "network": "Up to 5 Gbps", "family": InstanceFamily.BURSTABLE},
            "t3.2xlarge": {"vcpu": 8, "memory": 32, "network": "Up to 5 Gbps", "family": InstanceFamily.BURSTABLE},
        }
        
        logger.info(f"Instance Recommendation Service initialized with {len(self.instance_specs)} instance types")
    
    def recommend_instance(self, vm_spec: VMSpecification) -> InstanceRecommendation:
        """
        Recommend optimal AWS instance type for a VM specification
        """
        logger.info(f"Generating recommendation for VM: {vm_spec.vm_name} ({vm_spec.cpu_cores} vCPU, {vm_spec.memory_gb} GB RAM)")
        
        # Calculate CPU-to-memory ratio
        cpu_memory_ratio = vm_spec.cpu_cores / vm_spec.memory_gb if vm_spec.memory_gb > 0 else 1.0
        
        # Determine optimal instance family based on workload characteristics
        target_family = self._determine_instance_family(vm_spec, cpu_memory_ratio)
        
        # Find best matching instances
        candidates = self._find_candidate_instances(vm_spec, target_family)
        
        if not candidates:
            # Fallback to any suitable instance if no family-specific match
            candidates = self._find_candidate_instances(vm_spec, None)
        
        if not candidates:
            # Last resort - recommend a default instance
            return self._get_default_recommendation(vm_spec)
        
        # Score and rank candidates
        best_candidate = self._score_and_rank_candidates(vm_spec, candidates)
        
        return best_candidate
    
    def recommend_multiple_instances(self, vm_specs: List[VMSpecification]) -> List[InstanceRecommendation]:
        """
        Recommend instances for multiple VMs
        """
        logger.info(f"Generating recommendations for {len(vm_specs)} VMs")
        
        recommendations = []
        for vm_spec in vm_specs:
            try:
                recommendation = self.recommend_instance(vm_spec)
                recommendations.append(recommendation)
            except Exception as e:
                logger.error(f"Failed to generate recommendation for {vm_spec.vm_name}: {e}")
                # Add default recommendation for failed cases
                recommendations.append(self._get_default_recommendation(vm_spec))
        
        return recommendations
    
    def _determine_instance_family(self, vm_spec: VMSpecification, cpu_memory_ratio: float) -> InstanceFamily:
        """
        Determine optimal instance family based on VM characteristics
        """
        # Memory-intensive workloads (low CPU-to-memory ratio)
        if cpu_memory_ratio < 0.25:  # Less than 1 vCPU per 4 GB RAM
            return InstanceFamily.MEMORY_OPTIMIZED
        
        # CPU-intensive workloads (high CPU-to-memory ratio)
        elif cpu_memory_ratio > 0.75:  # More than 3 vCPU per 4 GB RAM
            return InstanceFamily.COMPUTE_OPTIMIZED
        
        # Development/testing workloads with low resource requirements
        elif (vm_spec.workload_type in [WorkloadType.DEVELOPMENT, WorkloadType.TESTING] and 
              vm_spec.cpu_cores <= 4 and vm_spec.memory_gb <= 16):
            return InstanceFamily.BURSTABLE
        
        # Balanced workloads
        else:
            return InstanceFamily.GENERAL_PURPOSE
    
    def _find_candidate_instances(self, vm_spec: VMSpecification, target_family: Optional[InstanceFamily]) -> List[str]:
        """
        Find candidate instance types that meet VM requirements
        """
        candidates = []
        
        for instance_type, specs in self.instance_specs.items():
            # Filter by family if specified
            if target_family and specs["family"] != target_family:
                continue
            
            # Must meet minimum CPU requirements
            if specs["vcpu"] < vm_spec.cpu_cores:
                continue
            
            # Must meet minimum memory requirements
            if specs["memory"] < vm_spec.memory_gb:
                continue
            
            # Don't over-provision too much (within 4x of requirements)
            if specs["vcpu"] > vm_spec.cpu_cores * 4:
                continue
            
            if specs["memory"] > vm_spec.memory_gb * 4:
                continue
            
            candidates.append(instance_type)
        
        logger.info(f"Found {len(candidates)} candidate instances for {vm_spec.vm_name}")
        return candidates
    
    def _score_and_rank_candidates(self, vm_spec: VMSpecification, candidates: List[str]) -> InstanceRecommendation:
        """
        Score and rank candidate instances to find the best match
        """
        scored_candidates = []
        
        for instance_type in candidates:
            specs = self.instance_specs[instance_type]
            
            # Performance match score (how well it matches requirements)
            cpu_match = min(1.0, vm_spec.cpu_cores / specs["vcpu"])
            memory_match = min(1.0, vm_spec.memory_gb / specs["memory"])
            performance_score = (cpu_match + memory_match) / 2
            
            # Cost efficiency score (prefer smaller instances that meet requirements)
            cpu_efficiency = vm_spec.cpu_cores / specs["vcpu"]
            memory_efficiency = vm_spec.memory_gb / specs["memory"]
            cost_efficiency = (cpu_efficiency + memory_efficiency) / 2
            
            # Overall confidence score
            confidence = (performance_score * 0.6) + (cost_efficiency * 0.4)
            
            scored_candidates.append({
                "instance_type": instance_type,
                "confidence": confidence,
                "performance_score": performance_score,
                "cost_efficiency": cost_efficiency,
                "specs": specs
            })
        
        # Sort by confidence score (descending)
        scored_candidates.sort(key=lambda x: x["confidence"], reverse=True)
        
        # Get the best candidate
        best = scored_candidates[0]
        
        # Generate reasoning
        reasoning = self._generate_reasoning(vm_spec, best)
        
        # Get alternative options (top 3 alternatives)
        alternatives = [c["instance_type"] for c in scored_candidates[1:4]]
        
        return InstanceRecommendation(
            instance_type=best["instance_type"],
            instance_family=best["specs"]["family"],
            vcpu=best["specs"]["vcpu"],
            memory_gb=best["specs"]["memory"],
            confidence_score=best["confidence"],
            reasoning=reasoning,
            cost_efficiency_score=best["cost_efficiency"],
            performance_match_score=best["performance_score"],
            alternative_options=alternatives
        )
    
    def _generate_reasoning(self, vm_spec: VMSpecification, best_candidate: Dict) -> str:
        """
        Generate human-readable reasoning for the recommendation
        """
        instance_type = best_candidate["instance_type"]
        specs = best_candidate["specs"]
        
        reasoning_parts = []
        
        # Basic match explanation
        reasoning_parts.append(f"Recommended {instance_type} for {vm_spec.vm_name}")
        reasoning_parts.append(f"Provides {specs['vcpu']} vCPUs (required: {vm_spec.cpu_cores}) and {specs['memory']} GB RAM (required: {vm_spec.memory_gb} GB)")
        
        # Family explanation
        family_reasons = {
            InstanceFamily.GENERAL_PURPOSE: "balanced CPU and memory for general workloads",
            InstanceFamily.COMPUTE_OPTIMIZED: "optimized for CPU-intensive workloads",
            InstanceFamily.MEMORY_OPTIMIZED: "optimized for memory-intensive workloads",
            InstanceFamily.BURSTABLE: "cost-effective for variable workloads"
        }
        reasoning_parts.append(f"Selected from {specs['family'].value} family - {family_reasons[specs['family']]}")
        
        # Workload type consideration
        if vm_spec.workload_type != WorkloadType.PRODUCTION:
            reasoning_parts.append(f"Considered {vm_spec.workload_type.value} workload characteristics")
        
        # Efficiency note
        cpu_utilization = (vm_spec.cpu_cores / specs['vcpu']) * 100
        memory_utilization = (vm_spec.memory_gb / specs['memory']) * 100
        reasoning_parts.append(f"Resource utilization: {cpu_utilization:.0f}% CPU, {memory_utilization:.0f}% memory")
        
        return ". ".join(reasoning_parts)
    
    def _get_default_recommendation(self, vm_spec: VMSpecification) -> InstanceRecommendation:
        """
        Provide a default recommendation when no suitable match is found
        """
        # Default to m5.large for small workloads, m5.xlarge for larger ones
        if vm_spec.cpu_cores <= 2 and vm_spec.memory_gb <= 8:
            default_instance = "m5.large"
        elif vm_spec.cpu_cores <= 4 and vm_spec.memory_gb <= 16:
            default_instance = "m5.xlarge"
        elif vm_spec.cpu_cores <= 8 and vm_spec.memory_gb <= 32:
            default_instance = "m5.2xlarge"
        else:
            default_instance = "m5.4xlarge"
        
        specs = self.instance_specs[default_instance]
        
        return InstanceRecommendation(
            instance_type=default_instance,
            instance_family=specs["family"],
            vcpu=specs["vcpu"],
            memory_gb=specs["memory"],
            confidence_score=0.5,  # Low confidence for default recommendations
            reasoning=f"Default recommendation for {vm_spec.vm_name} - no optimal match found for {vm_spec.cpu_cores} vCPU, {vm_spec.memory_gb} GB RAM requirements",
            cost_efficiency_score=0.5,
            performance_match_score=0.5,
            alternative_options=["m5.xlarge", "m5.2xlarge", "m5.4xlarge"]
        )
    
    def get_instance_families_summary(self) -> Dict[str, Dict]:
        """
        Get summary of available instance families
        """
        families = {}
        
        for instance_type, specs in self.instance_specs.items():
            family = specs["family"].value
            if family not in families:
                families[family] = {
                    "instance_count": 0,
                    "vcpu_range": {"min": float('inf'), "max": 0},
                    "memory_range": {"min": float('inf'), "max": 0},
                    "instance_types": []
                }
            
            families[family]["instance_count"] += 1
            families[family]["vcpu_range"]["min"] = min(families[family]["vcpu_range"]["min"], specs["vcpu"])
            families[family]["vcpu_range"]["max"] = max(families[family]["vcpu_range"]["max"], specs["vcpu"])
            families[family]["memory_range"]["min"] = min(families[family]["memory_range"]["min"], specs["memory"])
            families[family]["memory_range"]["max"] = max(families[family]["memory_range"]["max"], specs["memory"])
            families[family]["instance_types"].append(instance_type)
        
        return families

# Global instance recommendation service
recommendation_service = InstanceRecommendationService()
