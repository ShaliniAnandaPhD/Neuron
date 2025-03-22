"""
exceptions.py - Custom Exceptions for Neuron Framework

This module defines a hierarchy of custom exceptions that provide informative
error messages and proper categorization of different error types that can
occur within the Neuron framework.

Having a well-structured exception hierarchy allows for precise error handling
and helps developers diagnose issues more effectively.
"""

class NeuronException(Exception):
    """
    Base exception for all Neuron framework errors.
    
    This serves as the parent class for all framework-specific exceptions,
    allowing developers to catch all Neuron-related exceptions with a single
    except clause if desired.
    """
    pass


# Core System Exceptions

class ConfigurationError(NeuronException):
    """
    Raised when there's an error in the framework configuration.
    
    Examples include invalid configuration values, missing required
    configuration parameters, or configuration that creates an invalid state.
    """
    pass


class ValidationError(NeuronException):
    """
    Raised when validation of any component, message, or structure fails.
    
    This includes schema validation, format validation, and logical
    validation of structures and connections.
    """
    pass


# Agent-Related Exceptions

class AgentError(NeuronException):
    """Base class for all agent-related exceptions."""
    pass


class AgentInitializationError(AgentError):
    """
    Raised when an agent fails to initialize properly.
    
    This could be due to missing dependencies, invalid configuration,
    or failure to connect to required services.
    """
    pass


class AgentProcessingError(AgentError):
    """
    Raised when an agent encounters an error during message processing.
    
    This is typically used when the agent's core processing logic fails,
    but the agent itself is still functional.
    """
    pass


class AgentCapabilityError(AgentError):
    """
    Raised when an agent is asked to perform a capability it doesn't have.
    
    This helps identify mismatches between expected and actual agent capabilities,
    which is crucial for proper circuit design.
    """
    pass


# Memory-Related Exceptions

class MemoryError(NeuronException):
    """Base class for all memory-related exceptions."""
    pass


class MemoryAccessError(MemoryError):
    """
    Raised when there's an error accessing memory.
    
    Examples include attempting to access non-existent memory entries
    or permission issues for protected memories.
    """
    pass


class MemoryStorageError(MemoryError):
    """
    Raised when there's an error storing information in memory.
    
    This could happen due to validation failures, storage limits,
    or backend storage issues.
    """
    pass


# Communication-Related Exceptions

class CommunicationError(NeuronException):
    """Base class for all communication-related exceptions."""
    pass


class SynapticBusError(CommunicationError):
    """
    Raised when there's an error in the SynapticBus communication system.
    
    This includes message routing errors, channel configuration issues,
    and message delivery failures.
    """
    pass


class MessageValidationError(CommunicationError):
    """
    Raised when a message fails validation.
    
    This helps identify malformed messages or messages with invalid content
    before they propagate through the system.
    """
    pass


class ChannelError(CommunicationError):
    """
    Raised when there's an error with a specific communication channel.
    
    Examples include channel creation failures, subscription issues,
    and channel capacity problems.
    """
    pass


# Circuit-Related Exceptions

class CircuitError(NeuronException):
    """Base class for all circuit-related exceptions."""
    pass


class CircuitDesignerError(CircuitError):
    """
    Raised when there's an error in circuit design or validation.
    
    This helps identify issues with circuit structure, agent connections,
    or other design-time problems.
    """
    pass


class CircuitRuntimeError(CircuitError):
    """
    Raised when a circuit encounters a runtime error.
    
    This is used for errors that occur during circuit operation,
    such as deadlocks, message flow issues, or agent failures.
    """
    pass


# Monitoring-Related Exceptions

class MonitoringError(NeuronException):
    """
    Raised when there's an error in the monitoring system.
    
    This includes metric collection failures, visualization errors,
    and alerting problems.
    """
    pass


# Extension-Related Exceptions

class ExtensionError(NeuronException):
    """
    Raised when there's an error loading or using a framework extension.
    
    This helps identify compatibility issues or problems with
    third-party extensions.
    """
    pass


class PluginError(ExtensionError):
    """
    Raised when there's an error with a specific plugin.
    
    This includes plugin initialization failures, compatibility issues,
    and plugin runtime errors.
    """
    pass


# Integration-Related Exceptions

class IntegrationError(NeuronException):
    """
    Raised when there's an error integrating with external systems.
    
    This helps identify issues with external APIs, services,
    or data sources that the framework interacts with.
    """
    pass


# Resource-Related Exceptions

class ResourceError(NeuronException):
    """Base class for all resource-related exceptions."""
    pass


class ResourceExhaustedError(ResourceError):
    """
    Raised when a resource limit is reached.
    
    Examples include memory limits, API rate limits,
    or computational resource constraints.
    """
    pass


class ResourceNotFoundError(ResourceError):
    """
    Raised when a requested resource cannot be found.
    
    This includes missing files, unavailable services,
    or references to non-existent entities.
    """
    pass
"""
