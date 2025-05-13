"""
Trace Viewer Module for Neuron Architecture

Provides CLI or browser-based tools for visualizing and 
stepping through circuit execution traces.
"""

import os
import json
import time
import logging
import argparse
import webbrowser
from pathlib import Path
from typing import Dict, List, Any, Optional, Union, Set, Callable
from datetime import datetime, timedelta
import http.server
import socketserver
import threading
import tempfile
import shutil

logger = logging.getLogger(__name__)

# HTML templates for visualization
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Neuron Trace Viewer</title>
    <style>
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            line-height: 1.6;
            color: #333;
            margin: 0;
            padding: 0;
            background-color: #f8f9fa;
        }
        .container {
            display: flex;
            height: 100vh;
        }
        .sidebar {
            width: 300px;
            background-color: #343a40;
            color: #fff;
            padding: 20px;
            overflow-y: auto;
        }
        .content {
            flex: 1;
            padding: 20px;
            overflow-y: auto;
        }
        .tabs {
            display: flex;
            border-bottom: 1px solid #dee2e6;
            margin-bottom: 20px;
        }
        .tab {
            padding: 10px 20px;
            cursor: pointer;
            border: 1px solid transparent;
        }
        .tab.active {
            border: 1px solid #dee2e6;
            border-bottom-color: #fff;
            background-color: #fff;
            margin-bottom: -1px;
        }
        .tab-content {
            display: none;
        }
        .tab-content.active {
            display: block;
        }
        .trace-item {
            padding: 10px;
            margin-bottom: 10px;
            cursor: pointer;
            border-left: 3px solid transparent;
        }
        .trace-item:hover {
            background-color: #49505a;
        }
        .trace-item.selected {
            border-left-color: #007bff;
            background-color: #49505a;
        }
        .event-item {
            padding: 10px;
            margin-bottom: 5px;
            border-radius: 4px;
            border-left: 4px solid #6c757d;
        }
        .event-item:hover {
            background-color: #f1f3f5;
        }
        .event-item.selected {
            background-color: #e2e6ea;
        }
        .event-agent-call { border-left-color: #28a745; }
        .event-memory-access { border-left-color: #fd7e14; }
        .event-circuit-execution { border-left-color: #007bff; }
        .event-error { border-left-color: #dc3545; }
        .event-span-start { border-left-color: #20c997; }
        .event-span-end { border-left-color: #20c997; }
        .event-agent-failure { border-left-color: #dc3545; }
        .event-fallback-result { border-left-color: #6f42c1; }
        pre {
            background-color: #f8f9fa;
            padding: 15px;
            border-radius: 4px;
            overflow-x: auto;
        }
        .event-time {
            font-size: 0.8em;
            color: #6c757d;
        }
        .btn {
            padding: 8px 16px;
            background-color: #007bff;
            color: white;
            border: none;
            border-radius: 4px;
            cursor: pointer;
        }
        .btn:hover {
            background-color: #0069d9;
        }
        .timeline {
            position: relative;
            margin: 20px 0;
            padding-bottom: 20px;
        }
        .timeline-bar {
            position: absolute;
            left: 0;
            right: 0;
            height: 4px;
            background-color: #dee2e6;
            top: 20px;
        }
        .timeline-events {
            position: relative;
            height: 40px;
        }
        .timeline-event {
            position: absolute;
            width: 10px;
            height: 10px;
            border-radius: 50%;
            background-color: #6c757d;
            top: 17px;
            transform: translateX(-50%);
            cursor: pointer;
        }
        .timeline-event.active {
            background-color: #007bff;
            width: 14px;
            height: 14px;
            top: 15px;
        }
        .timeline-event:hover {
            transform: translateX(-50%) scale(1.2);
        }
        .badge {
            display: inline-block;
            padding: 4px 8px;
            border-radius: 4px;
            font-size: 0.8em;
            font-weight: 600;
            color: white;
        }
        .badge-success { background-color: #28a745; }
        .badge-danger { background-color: #dc3545; }
        .badge-warning { background-color: #fd7e14; }
        .badge-info { background-color: #17a2b8; }
        .badge-primary { background-color: #007bff; }
        .badge-secondary { background-color: #6c757d; }
        .filter-section {
            margin-bottom: 20px;
            padding: 10px;
            background-color: #49505a;
            border-radius: 4px;
        }
        .search-box {
            width: 100%;
            padding: 8px;
            margin-bottom: 10px;
            border-radius: 4px;
            border: 1px solid #ced4da;
        }
        .span-marker {
            display: inline-block;
            width: 12px;
            height: 12px;
            margin-right: 5px;
            border-radius: 2px;
        }
        .span-container {
            margin: 10px 0;
            padding: 10px;
            border-radius: 4px;
        }
        .chart-container {
            height: 300px;
            margin: 20px 0;
        }
        details {
            margin: 5px 0;
        }
        summary {
            cursor: pointer;
            padding: 8px;
            background-color: #f1f3f5;
            border-radius: 4px;
        }
        .timestamp-label {
            font-family: monospace;
            font-size: 0.8em;
            color: #6c757d;
            margin-top: 5px;
        }
        .error-message {
            color: #dc3545;
            margin: 15px 0;
            padding: 10px;
            background-color: #f8d7da;
            border-radius: 4px;
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="sidebar">
            <h2>Neuron Traces</h2>
            <div class="filter-section">
                <input type="text" id="search-box" class="search-box" placeholder="Search traces...">
                <div>
                    <label><input type="checkbox" id="filter-completed" checked> Completed</label>
                    <label><input type="checkbox" id="filter-running" checked> Running</label>
                    <label><input type="checkbox" id="filter-error" checked> Error</label>
                </div>
            </div>
            <div id="trace-list">
                <!-- Trace items will be inserted here -->
                {trace_list_items}
            </div>
        </div>
        <div class="content">
            <div id="trace-details">
                <h2 id="trace-title">Select a trace</h2>
                <div id="trace-metadata"></div>
                
                <div class="tabs">
                    <div class="tab active" data-tab="events">Events</div>
                    <div class="tab" data-tab="spans">Spans</div>
                    <div class="tab" data-tab="timeline">Timeline</div>
                    <div class="tab" data-tab="stats">Stats</div>
                </div>
                
                <div class="tab-content active" id="events-tab">
                    <div class="filter-section">
                        <input type="text" id="event-filter" class="search-box" placeholder="Filter events...">
                        <div>
                            <label><input type="checkbox" class="event-type-filter" data-type="agent_call" checked> Agent Calls</label>
                            <label><input type="checkbox" class="event-type-filter" data-type="memory_access" checked> Memory Access</label>
                            <label><input type="checkbox" class="event-type-filter" data-type="circuit_execution" checked> Circuit Execution</label>
                            <label><input type="checkbox" class="event-type-filter" data-type="error" checked> Errors</label>
                            <label><input type="checkbox" class="event-type-filter" data-type="span" checked> Spans</label>
                        </div>
                    </div>
                    <div id="event-timeline" class="timeline">
                        <div class="timeline-bar"></div>
                        <div class="timeline-events" id="timeline-events-container">
                            <!-- Timeline events will be inserted here -->
                        </div>
                    </div>
                    <div id="events-list">
                        <!-- Event items will be inserted here -->
                        <p>Select a trace to view events</p>
                    </div>
                </div>
                
                <div class="tab-content" id="spans-tab">
                    <div id="spans-visualization">
                        <!-- Spans visualization will be inserted here -->
                        <p>Select a trace to view spans</p>
                    </div>
                </div>
                
                <div class="tab-content" id="timeline-tab">
                    <div class="chart-container" id="timeline-chart">
                        <!-- Timeline chart will be inserted here -->
                    </div>
                </div>
                
                <div class="tab-content" id="stats-tab">
                    <div id="stats-content">
                        <!-- Stats content will be inserted here -->
                        <p>Select a trace to view stats</p>
                    </div>
                </div>
            </div>
            
            <div id="event-details">
                <h3>Event Details</h3>
                <div id="event-content">
                    <!-- Event details will be inserted here -->
                    <p>Select an event to view details</p>
                </div>
            </div>
        </div>
    </div>

    <script>
        // Trace data
        const traceData = {trace_data_json};
        
        // Current selected trace and event
        let selectedTraceId = null;
        let selectedEventId = null;
        
        // Initialize the page
        document.addEventListener('DOMContentLoaded', () => {
            initTabs();
            initTraceList();
            initEventFilters();
        });
        
        // Initialize tabs
        function initTabs() {
            const tabs = document.querySelectorAll('.tab');
            tabs.forEach(tab => {
                tab.addEventListener('click', () => {
                    // Remove active class from all tabs
                    tabs.forEach(t => t.classList.remove('active'));
                    // Add active class to clicked tab
                    tab.classList.add('active');
                    
                    // Hide all tab content
                    const tabContents = document.querySelectorAll('.tab-content');
                    tabContents.forEach(content => content.classList.remove('active'));
                    
                    // Show selected tab content
                    const tabName = tab.getAttribute('data-tab');
                    document.getElementById(tabName + '-tab').classList.add('active');
                });
            });
        }
        
        // Initialize trace list
        function initTraceList() {
            const traceList = document.getElementById('trace-list');
            const searchBox = document.getElementById('search-box');
            const filterCompleted = document.getElementById('filter-completed');
            const filterRunning = document.getElementById('filter-running');
            const filterError = document.getElementById('filter-error');
            
            // Apply filters when changed
            searchBox.addEventListener('input', updateTraceList);
            filterCompleted.addEventListener('change', updateTraceList);
            filterRunning.addEventListener('change', updateTraceList);
            filterError.addEventListener('change', updateTraceList);
            
            // Initial trace list update
            updateTraceList();
        }
        
        // Update trace list based on filters
        function updateTraceList() {
            const traceList = document.getElementById('trace-list');
            const searchTerm = document.getElementById('search-box').value.toLowerCase();
            const showCompleted = document.getElementById('filter-completed').checked;
            const showRunning = document.getElementById('filter-running').checked;
            const showError = document.getElementById('filter-error').checked;
            
            // Clear trace list
            traceList.innerHTML = '';
            
            // Add traces that match filters
            Object.values(traceData).forEach(trace => {
                // Check status filter
                let showByStatus = false;
                if (trace.status === 'completed' && showCompleted) showByStatus = true;
                if (trace.status === 'running' && showRunning) showByStatus = true;
                if (trace.status === 'error' && showError) showByStatus = true;
                
                // Check search filter
                const traceText = JSON.stringify(trace).toLowerCase();
                const matchesSearch = searchTerm === '' || traceText.includes(searchTerm);
                
                if (showByStatus && matchesSearch) {
                    const traceItem = document.createElement('div');
                    traceItem.classList.add('trace-item');
                    traceItem.setAttribute('data-trace-id', trace.trace_id);
                    
                    // Status badge
                    let statusBadge = '';
                    if (trace.status === 'completed') {
                        statusBadge = '<span class="badge badge-success">Completed</span>';
                    } else if (trace.status === 'running') {
                        statusBadge = '<span class="badge badge-info">Running</span>';
                    } else if (trace.status === 'error') {
                        statusBadge = '<span class="badge badge-danger">Error</span>';
                    }
                    
                    // Format timestamp
                    const date = new Date(trace.start_time * 1000);
                    const timeString = date.toLocaleTimeString();
                    
                    traceItem.innerHTML = `
                        <div><strong>${statusBadge} ${trace.metadata?.name || 'Trace ' + trace.trace_id.substr(0, 8)}</strong></div>
                        <div class="event-time">${timeString} · ${trace.event_count || 0} events</div>
                    `;
                    
                    traceItem.addEventListener('click', () => selectTrace(trace.trace_id));
                    traceList.appendChild(traceItem);
                }
            });
            
            if (traceList.children.length === 0) {
                traceList.innerHTML = '<p>No traces match the filters</p>';
            }
        }
        
        // Select a trace
        function selectTrace(traceId) {
            selectedTraceId = traceId;
            
            // Update UI
            const traceItems = document.querySelectorAll('.trace-item');
            traceItems.forEach(item => {
                item.classList.remove('selected');
                if (item.getAttribute('data-trace-id') === traceId) {
                    item.classList.add('selected');
                }
            });
            
            // Update trace details
            updateTraceDetails(traceId);
        }
        
        // Update trace details
        function updateTraceDetails(traceId) {
            const trace = traceData[traceId];
            if (!trace) return;
            
            // Update title and metadata
            document.getElementById('trace-title').textContent = trace.metadata?.name || 'Trace ' + trace.trace_id.substr(0, 8);
            
            const metadataElement = document.getElementById('trace-metadata');
            
            // Format timestamps
            const startDate = new Date(trace.start_time * 1000);
            const startTimeString = startDate.toLocaleString();
            
            let durationStr = '';
            if (trace.duration) {
                const duration = trace.duration;
                if (duration < 1) {
                    durationStr = `${Math.round(duration * 1000)}ms`;
                } else if (duration < 60) {
                    durationStr = `${duration.toFixed(2)}s`;
                } else {
                    const minutes = Math.floor(duration / 60);
                    const seconds = Math.round(duration % 60);
                    durationStr = `${minutes}m ${seconds}s`;
                }
            }
            
            let statusBadge = '';
            if (trace.status === 'completed') {
                statusBadge = '<span class="badge badge-success">Completed</span>';
            } else if (trace.status === 'running') {
                statusBadge = '<span class="badge badge-info">Running</span>';
            } else if (trace.status === 'error') {
                statusBadge = '<span class="badge badge-danger">Error</span>';
            }
            
            // Create metadata HTML
            metadataElement.innerHTML = `
                <p>${statusBadge} Started: ${startTimeString}</p>
                ${trace.duration ? `<p>Duration: ${durationStr}</p>` : ''}
                <p>Events: ${trace.events?.length || 0}</p>
                <p>Spans: ${trace.spans?.length || 0}</p>
                ${trace.metadata ? `
                    <details>
                        <summary>Metadata</summary>
                        <pre>${JSON.stringify(trace.metadata, null, 2)}</pre>
                    </details>
                ` : ''}
            `;
            
            // Update events list
            updateEventsList(trace);
            
            // Update spans visualization
            updateSpansVisualization(trace);
            
            // Update timeline
            updateTimeline(trace);
            
            // Update stats
            updateStats(trace);
        }
        
        // Initialize event filters
        function initEventFilters() {
            const eventFilter = document.getElementById('event-filter');
            const typeFilters = document.querySelectorAll('.event-type-filter');
            
            // Apply filters when changed
            eventFilter.addEventListener('input', () => {
                if (selectedTraceId) {
                    updateEventsList(traceData[selectedTraceId]);
                }
            });
            
            typeFilters.forEach(filter => {
                filter.addEventListener('change', () => {
                    if (selectedTraceId) {
                        updateEventsList(traceData[selectedTraceId]);
                    }
                });
            });
        }
        
        // Update events list
        function updateEventsList(trace) {
            const eventsList = document.getElementById('events-list');
            const eventFilter = document.getElementById('event-filter').value.toLowerCase();
            const timelineEvents = document.getElementById('timeline-events-container');
            
            // Clear events list and timeline
            eventsList.innerHTML = '';
            timelineEvents.innerHTML = '';
            
            if (!trace.events || trace.events.length === 0) {
                eventsList.innerHTML = '<p>No events in this trace</p>';
                return;
            }
            
            // Get enabled event types
            const enabledTypes = {};
            document.querySelectorAll('.event-type-filter').forEach(filter => {
                enabledTypes[filter.getAttribute('data-type')] = filter.checked;
            });
            
            // Calculate timeline positioning
            const startTime = trace.start_time;
            const endTime = trace.end_time || (startTime + trace.duration) || 
                            (trace.events[trace.events.length - 1]?.timestamp || startTime + 1);
            const timeRange = endTime - startTime;
            
            // Add events that match filters
            trace.events.forEach((event, index) => {
                // Map event type to filter type
                let filterType = 'other';
                if (event.event_type.includes('agent')) filterType = 'agent_call';
                if (event.event_type.includes('memory')) filterType = 'memory_access';
                if (event.event_type.includes('circuit')) filterType = 'circuit_execution';
                if (event.event_type.includes('error')) filterType = 'error';
                if (event.event_type.includes('span')) filterType = 'span';
                
                // Check if type is enabled
                const typeEnabled = enabledTypes[filterType] || false;
                
                // Check if matches text filter
                const eventText = JSON.stringify(event).toLowerCase();
                const matchesText = eventFilter === '' || eventText.includes(eventFilter);
                
                if (typeEnabled && matchesText) {
                    // Create event item
                    const eventItem = document.createElement('div');
                    eventItem.classList.add('event-item');
                    eventItem.classList.add(`event-${event.event_type.replace(/[^a-zA-Z0-9]/g, '-')}`);
                    eventItem.setAttribute('data-event-id', index);
                    
                    // Format timestamp
                    const timeOffset = (event.timestamp - startTime).toFixed(3);
                    
                    eventItem.innerHTML = `
                        <div><strong>${event.event_type}</strong> - ${event.component_id}</div>
                        <div class="event-time">+${timeOffset}s</div>
                    `;
                    
                    eventItem.addEventListener('click', () => selectEvent(trace.trace_id, index));
                    eventsList.appendChild(eventItem);
                    
                    // Add to timeline
                    const position = ((event.timestamp - startTime) / timeRange) * 100;
                    const timelineEvent = document.createElement('div');
                    timelineEvent.classList.add('timeline-event');
                    timelineEvent.style.left = `${position}%`;
                    timelineEvent.setAttribute('data-event-id', index);
                    timelineEvent.setAttribute('title', `${event.event_type} - ${timeOffset}s`);
                    
                    timelineEvent.addEventListener('click', () => selectEvent(trace.trace_id, index));
                    timelineEvents.appendChild(timelineEvent);
                }
            });
            
            if (eventsList.children.length === 0) {
                eventsList.innerHTML = '<p>No events match the filters</p>';
            }
        }
        
        // Select an event
        function selectEvent(traceId, eventIndex) {
            selectedTraceId = traceId;
            selectedEventId = eventIndex;
            
            // Update UI
            const eventItems = document.querySelectorAll('.event-item');
            eventItems.forEach(item => {
                item.classList.remove('selected');
                if (parseInt(item.getAttribute('data-event-id')) === eventIndex) {
                    item.classList.add('selected');
                    item.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
                }
            });
            
            const timelineEvents = document.querySelectorAll('.timeline-event');
            timelineEvents.forEach(item => {
                item.classList.remove('active');
                if (parseInt(item.getAttribute('data-event-id')) === eventIndex) {
                    item.classList.add('active');
                }
            });
            
            // Update event details
            updateEventDetails(traceId, eventIndex);
        }
        
        // Update event details
        function updateEventDetails(traceId, eventIndex) {
            const trace = traceData[traceId];
            if (!trace || !trace.events || eventIndex >= trace.events.length) return;
            
            const event = trace.events[eventIndex];
            const eventContent = document.getElementById('event-content');
            
            // Format timestamp
            const date = new Date(event.timestamp * 1000);
            const timeString = date.toLocaleString();
            const timeOffset = (event.timestamp - trace.start_time).toFixed(3);
            
            // Create event details HTML
            eventContent.innerHTML = `
                <p><strong>Event Type:</strong> ${event.event_type}</p>
                <p><strong>Component:</strong> ${event.component_id}</p>
                <p><strong>Timestamp:</strong> ${timeString} (+${timeOffset}s)</p>
                ${event.span_id ? `<p><strong>Span ID:</strong> ${event.span_id}</p>` : ''}
                ${event.sequence ? `<p><strong>Sequence:</strong> ${event.sequence}</p>` : ''}
                
                <details open>
                    <summary>Event Data</summary>
                    <pre>${JSON.stringify(event.data, null, 2)}</pre>
                </details>
                
                <div class="timestamp-label">Event ID: ${event.event_id}</div>
            `;
        }
        
        // Update spans visualization
        function updateSpansVisualization(trace) {
            const spansContainer = document.getElementById('spans-visualization');
            
            if (!trace.spans || trace.spans.length === 0) {
                spansContainer.innerHTML = '<p>No spans in this trace</p>';
                return;
            }
            
            // Clear spans container
            spansContainer.innerHTML = '';
            
            // Create spans HTML
            const startTime = trace.start_time;
            const endTime = trace.end_time || (startTime + trace.duration) || 
                           (trace.spans[trace.spans.length - 1]?.end_time || startTime + 1);
            const timeRange = endTime - startTime;
            
            // Sort spans by start time
            const sortedSpans = [...trace.spans].sort((a, b) => a.start_time - b.start_time);
            
            // Create spans visualization
            sortedSpans.forEach(span => {
                // Calculate time positions
                const spanStart = (span.start_time - startTime) / timeRange * 100;
                const spanEnd = span.end_time ? 
                               ((span.end_time - startTime) / timeRange * 100) : 100;
                const spanWidth = spanEnd - spanStart;
                
                // Format duration
                let durationStr = '';
                if (span.duration) {
                    const duration = span.duration;
                    if (duration < 1) {
                        durationStr = `${Math.round(duration * 1000)}ms`;
                    } else {
                        durationStr = `${duration.toFixed(2)}s`;
                    }
                }
                
                // Generate random color based on span type
                const hash = span.span_type.split('').reduce((acc, char) => {
                    return char.charCodeAt(0) + ((acc << 5) - acc);
                }, 0);
                const hue = Math.abs(hash % 360);
                const spanColor = `hsl(${hue}, 70%, 60%)`;
                
                const spanElement = document.createElement('div');
                spanElement.classList.add('span-container');
                spanElement.style.marginLeft = `${spanStart}%`;
                spanElement.style.width = `${spanWidth}%`;
                
                spanElement.innerHTML = `
                    <div>
                        <span class="span-marker" style="background-color: ${spanColor}"></span>
                        <strong>${span.span_type}</strong> - ${span.component_id}
                    </div>
                    <div class="event-time">
                        +${(span.start_time - startTime).toFixed(3)}s
                        ${span.duration ? `(${durationStr})` : ''}
                    </div>
                `;
                
                spansContainer.appendChild(spanElement);
            });
        }
        
        // Update timeline visualization
        function updateTimeline(trace) {
            const timelineChart = document.getElementById('timeline-chart');
            
            if (!trace.events || trace.events.length === 0) {
                timelineChart.innerHTML = '<p>No events to display timeline</p>';
                return;
            }
            
            // TODO: Implement more sophisticated timeline chart
            timelineChart.innerHTML = '<p>Timeline visualization coming soon</p>';
        }
        
        // Update statistics
        function updateStats(trace) {
            const statsContent = document.getElementById('stats-content');
            
            if (!trace.events || trace.events.length === 0) {
                statsContent.innerHTML = '<p>No events to compute statistics</p>';
                return;
            }
            
            // Analyze events
            const eventTypeCount = {};
            const componentCount = {};
            trace.events.forEach(event => {
                // Count event types
                if (!eventTypeCount[event.event_type]) {
                    eventTypeCount[event.event_type] = 0;
                }
                eventTypeCount[event.event_type]++;
                
                // Count components
                if (!componentCount[event.component_id]) {
                    componentCount[event.component_id] = 0;
                }
                componentCount[event.component_id]++;
            });
            
            // Analyze spans
            let avgSpanDuration = 0;
            let totalSpanTime = 0;
            let spanTypeCount = {};
            
            if (trace.spans && trace.spans.length > 0) {
                trace.spans.forEach(span => {
                    if (span.duration) {
                        totalSpanTime += span.duration;
                    }
                    
                    // Count span types
                    if (!spanTypeCount[span.span_type]) {
                        spanTypeCount[span.span_type] = 0;
                    }
                    spanTypeCount[span.span_type]++;
                });
                
                avgSpanDuration = totalSpanTime / trace.spans.length;
            }
            
            // Create stats HTML
            let statsHtml = `
                <h3>Event Statistics</h3>
                <p>Total Events: ${trace.events.length}</p>
                
                <h4>Event Types</h4>
                <ul>
                    ${Object.entries(eventTypeCount).map(([type, count]) => 
                        `<li>${type}: ${count} events</li>`
                    ).join('')}
                </ul>
                
                <h4>Active Components</h4>
                <ul>
                    ${Object.entries(componentCount).map(([component, count]) => 
                        `<li>${component}: ${count} events</li>`
                    ).join('')}
                </ul>
            `;
            
            if (trace.spans && trace.spans.length > 0) {
                statsHtml += `
                    <h3>Span Statistics</h3>
                    <p>Total Spans: ${trace.spans.length}</p>
                    <p>Average Span Duration: ${avgSpanDuration.toFixed(3)}s</p>
                    
                    <h4>Span Types</h4>
                    <ul>
                        ${Object.entries(spanTypeCount).map(([type, count]) => 
                            `<li>${type}: ${count} spans</li>`
                        ).join('')}
                    </ul>
                `;
            }
            
            statsContent.innerHTML = statsHtml;
        }
    </script>
</body>
</html>
"""

class TraceViewer:
    """
    Provides tools for visualizing and stepping through circuit execution traces
    from trace_logger output.
    """
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize the trace viewer with configuration parameters.
        
        Args:
            config: Configuration for trace viewer
        """
        # Basic configuration
        self.log_dir = Path(config.get("trace_log_dir", "./logs/traces"))
        self.host = config.get("server_host", "localhost")
        self.port = config.get("server_port", 8675)
        self.max_traces = config.get("max_traces", 100)
        self.debug = config.get("debug", False)
        
        # Specialized configuration
        self.auto_open_browser = config.get("auto_open_browser", True)
        self.refresh_interval = config.get("refresh_interval", 5)  # seconds
        self.dark_mode = config.get("dark_mode", False)
        
        # Server state
        self.server = None
        self.server_thread = None
        self.temp_dir = None
        
        # Initialize logging
        self._setup_logging()
        
    def _setup_logging(self) -> None:
        """Set up logging for the trace viewer."""
        if not logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
            handler.setFormatter(formatter)
            logger.addHandler(handler)
            logger.setLevel(logging.INFO)
            
            if self.debug:
                logger.setLevel(logging.DEBUG)
                
    def list_traces(self, max_count: int = None, 
                   filter_status: Optional[str] = None,
                   time_range: Optional[Tuple[float, float]] = None) -> List[Dict[str, Any]]:
        """
        List available traces with filtering options.
        
        Args:
            max_count: Maximum number of traces to return
            filter_status: Optional status to filter by ('completed', 'running', 'error')
            time_range: Optional (start_time, end_time) tuple
            
        Returns:
            traces: List of trace metadata
        """
        max_count = max_count or self.max_traces
        traces = []
        
        try:
            # List all trace files
            if not self.log_dir.exists():
                logger.warning(f"Trace log directory does not exist: {self.log_dir}")
                return []
                
            trace_files = list(self.log_dir.glob("*.json"))
            trace_files.sort(key=lambda x: x.stat().st_mtime, reverse=True)
            
            # Load trace data with filtering
            for file_path in trace_files[:max_count * 2]:  # Load more for filtering
                try:
                    with open(file_path, 'r') as f:
                        trace_data = json.load(f)
                        
                    # Apply status filter
                    if filter_status and trace_data.get("status") != filter_status:
                        continue
                        
                    # Apply time range filter
                    if time_range:
                        start_time, end_time = time_range
                        trace_start = trace_data.get("start_time", 0)
                        
                        if trace_start < start_time or trace_start > end_time:
                            continue
                            
                    # Add to results
                    traces.append({
                        "trace_id": trace_data.get("trace_id"),
                        "status": trace_data.get("status"),
                        "start_time": trace_data.get("start_time"),
                        "end_time": trace_data.get("end_time", None),
                        "duration": trace_data.get("duration", None),
                        "event_count": len(trace_data.get("events", [])),
                        "metadata": trace_data.get("metadata", {})
                    })
                    
                    # Stop if we have enough traces
                    if len(traces) >= max_count:
                        break
                        
                except Exception as e:
                    logger.warning(f"Error loading trace file {file_path}: {e}")
                    
            return traces
                
        except Exception as e:
            logger.error(f"Error listing traces: {e}")
            return []
    
    def get_trace(self, trace_id: str) -> Optional[Dict[str, Any]]:
        """
        Get a specific trace by ID.
        
        Args:
            trace_id: ID of the trace to retrieve
            
        Returns:
            trace: The trace data or None if not found
        """
        try:
            trace_file = self.log_dir / f"{trace_id}.json"
            
            if not trace_file.exists():
                logger.warning(f"Trace file not found: {trace_id}")
                return None
                
            with open(trace_file, 'r') as f:
                trace_data = json.load(f)
                
            return trace_data
                
        except Exception as e:
            logger.error(f"Error loading trace {trace_id}: {e}")
            return None
    
    def get_trace_events(self, trace_id: str, 
                       filter_type: Optional[str] = None,
                       component_id: Optional[str] = None,
                       limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        Get events from a specific trace with filtering.
        
        Args:
            trace_id: ID of the trace
            filter_type: Optional event type filter
            component_id: Optional component ID filter
            limit: Maximum number of events to return
            
        Returns:
            events: List of filtered events
        """
        trace = self.get_trace(trace_id)
        
        if not trace or "events" not in trace:
            return []
            
        events = trace["events"]
        
        # Apply filters
        if filter_type:
            events = [e for e in events if e.get("event_type") == filter_type]
            
        if component_id:
            events = [e for e in events if e.get("component_id") == component_id]
            
        # Apply limit
        if limit is not None:
            events = events[:limit]
            
        return events
    
    def get_trace_spans(self, trace_id: str, 
                      filter_type: Optional[str] = None,
                      component_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Get spans from a specific trace with filtering.
        
        Args:
            trace_id: ID of the trace
            filter_type: Optional span type filter
            component_id: Optional component ID filter
            
        Returns:
            spans: List of filtered spans
        """
        trace = self.get_trace(trace_id)
        
        if not trace or "spans" not in trace:
            return []
            
        spans = trace["spans"]
        
        # Apply filters
        if filter_type:
            spans = [s for s in spans if s.get("span_type") == filter_type]
            
        if component_id:
            spans = [s for s in spans if s.get("component_id") == component_id]
            
        return spans
    
    def analyze_trace(self, trace_id: str) -> Dict[str, Any]:
        """
        Analyze a trace to extract useful statistics and insights.
        
        Args:
            trace_id: ID of the trace to analyze
            
        Returns:
            analysis: Dictionary of analysis results
        """
        trace = self.get_trace(trace_id)
        
        if not trace:
            return {"error": "Trace not found"}
            
        analysis = {
            "trace_id": trace_id,
            "status": trace.get("status"),
            "duration": trace.get("duration"),
            "event_count": len(trace.get("events", [])),
            "span_count": len(trace.get("spans", [])),
            "event_types": {},
            "component_activity": {},
            "span_analysis": {},
            "timeline": {},
            "errors": []
        }
        
        # Analyze events
        events = trace.get("events", [])
        
        for event in events:
            event_type = event.get("event_type")
            component_id = event.get("component_id")
            
            # Count event types
            if event_type not in analysis["event_types"]:
                analysis["event_types"][event_type] = 0
            analysis["event_types"][event_type] += 1
            
            # Count component activity
            if component_id not in analysis["component_activity"]:
                analysis["component_activity"][component_id] = 0
            analysis["component_activity"][component_id] += 1
            
            # Collect errors
            if event_type in ["error", "exception", "agent_failure"]:
                analysis["errors"].append({
                    "event_id": event.get("event_id"),
                    "component_id": component_id,
                    "timestamp": event.get("timestamp"),
                    "error_data": event.get("data", {})
                })
                
        # Analyze spans
        spans = trace.get("spans", [])
        span_types = {}
        span_durations = {}
        unfinished_spans = []
        
        for span in spans:
            span_type = span.get("span_type")
            
            # Count span types
            if span_type not in span_types:
                span_types[span_type] = 0
            span_types[span_type] += 1
            
            # Collect durations
            if "duration" in span:
                if span_type not in span_durations:
                    span_durations[span_type] = []
                span_durations[span_type].append(span["duration"])
            elif span.get("status") != "completed":
                unfinished_spans.append(span.get("span_id"))
                
        # Calculate average durations
        avg_durations = {}
        for span_type, durations in span_durations.items():
            if durations:
                avg_durations[span_type] = sum(durations) / len(durations)
                
        analysis["span_analysis"] = {
            "span_types": span_types,
            "avg_durations": avg_durations,
            "unfinished_spans": unfinished_spans
        }
        
        # Analyze timeline
        if events:
            start_time = trace.get("start_time", events[0].get("timestamp"))
            end_time = trace.get("end_time", events[-1].get("timestamp"))
            
            # Divide into 10 time buckets
            if end_time > start_time:
                bucket_size = (end_time - start_time) / 10
                buckets = [0] * 10
                
                for event in events:
                    timestamp = event.get("timestamp")
                    if timestamp is not None:
                        bucket_idx = min(9, int((timestamp - start_time) / bucket_size))
                        buckets[bucket_idx] += 1
                        
                analysis["timeline"] = {
                    "start_time": start_time,
                    "end_time": end_time,
                    "bucket_size": bucket_size,
                    "buckets": buckets
                }
                
        return analysis
    
    def compare_traces(self, trace_id1: str, trace_id2: str) -> Dict[str, Any]:
        """
        Compare two traces to identify differences.
        
        Args:
            trace_id1: ID of the first trace
            trace_id2: ID of the second trace
            
        Returns:
            comparison: Dictionary of comparison results
        """
        trace1 = self.get_trace(trace_id1)
        trace2 = self.get_trace(trace_id2)
        
        if not trace1 or not trace2:
            return {"error": "One or both traces not found"}
            
        comparison = {
            "trace1_id": trace_id1,
            "trace2_id": trace_id2,
            "duration_diff": None,
            "event_count_diff": None,
            "span_count_diff": None,
            "event_type_diffs": {},
            "component_diffs": {},
            "error_diffs": {}
        }
        
        # Compare basic metrics
        if "duration" in trace1 and "duration" in trace2:
            comparison["duration_diff"] = trace2["duration"] - trace1["duration"]
            
        events1 = trace1.get("events", [])
        events2 = trace2.get("events", [])
        comparison["event_count_diff"] = len(events2) - len(events1)
        
        spans1 = trace1.get("spans", [])
        spans2 = trace2.get("spans", [])
        comparison["span_count_diff"] = len(spans2) - len(spans1)
        
        # Compare event types
        event_types1 = {}
        event_types2 = {}
        
        for event in events1:
            event_type = event.get("event_type")
            if event_type not in event_types1:
                event_types1[event_type] = 0
            event_types1[event_type] += 1
            
        for event in events2:
            event_type = event.get("event_type")
            if event_type not in event_types2:
                event_types2[event_type] = 0
            event_types2[event_type] += 1
            
        # Find differences in event types
        all_event_types = set(event_types1.keys()) | set(event_types2.keys())
        
        for event_type in all_event_types:
            count1 = event_types1.get(event_type, 0)
            count2 = event_types2.get(event_type, 0)
            
            if count1 != count2:
                comparison["event_type_diffs"][event_type] = {
                    "trace1_count": count1,
                    "trace2_count": count2,
                    "diff": count2 - count1
                }
                
        # Compare components
        components1 = {}
        components2 = {}
        
        for event in events1:
            component = event.get("component_id")
            if component not in components1:
                components1[component] = 0
            components1[component] += 1
            
        for event in events2:
            component = event.get("component_id")
            if component not in components2:
                components2[component] = 0
            components2[component] += 1
            
        # Find differences in components
        all_components = set(components1.keys()) | set(components2.keys())
        
        for component in all_components:
            count1 = components1.get(component, 0)
            count2 = components2.get(component, 0)
            
            if count1 != count2:
                comparison["component_diffs"][component] = {
                    "trace1_count": count1,
                    "trace2_count": count2,
                    "diff": count2 - count1
                }
                
        # Compare errors
        errors1 = [e for e in events1 if e.get("event_type") in ["error", "exception", "agent_failure"]]
        errors2 = [e for e in events2 if e.get("event_type") in ["error", "exception", "agent_failure"]]
        
        comparison["error_diffs"] = {
            "trace1_errors": len(errors1),
            "trace2_errors": len(errors2),
            "diff": len(errors2) - len(errors1)
        }
        
        return comparison
    
    def start_server(self, host: Optional[str] = None, port: Optional[int] = None) -> str:
        """
        Start a local web server to visualize traces.
        
        Args:
            host: Optional host address (default: from config)
            port: Optional port number (default: from config)
            
        Returns:
            url: URL of the web server
        """
        host = host or self.host
        port = port or self.port
        
        # Create temporary directory for server files
        self.temp_dir = tempfile.mkdtemp(prefix="neuron_trace_viewer_")
        
        # Load traces
        traces = {}
        for trace in self.list_traces():
            trace_id = trace["trace_id"]
            full_trace = self.get_trace(trace_id)
            if full_trace:
                traces[trace_id] = full_trace
                
        # Generate HTML
        html_content = HTML_TEMPLATE.replace(
            "{trace_data_json}", json.dumps(traces)
        ).replace(
            "{trace_list_items}", ""  # Generated by JavaScript
        )
        
        # Write HTML to temp directory
        html_path = Path(self.temp_dir) / "index.html"
        with open(html_path, 'w') as f:
            f.write(html_content)
            
        # Start HTTP server
        handler = http.server.SimpleHTTPRequestHandler
        
        class CustomHandler(handler):
            def __init__(self, *args, **kwargs):
                super().__init__(*args, directory=self.temp_dir, **kwargs)
                
        CustomHandler.temp_dir = self.temp_dir
        
        self.server = socketserver.TCPServer((host, port), CustomHandler)
        
        # Run server in a separate thread
        self.server_thread = threading.Thread(target=self.server.serve_forever)
        self.server_thread.daemon = True
        self.server_thread.start()
        
        url = f"http://{host}:{port}"
        logger.info(f"Trace viewer server started at {url}")
        
        # Open browser if configured
        if self.auto_open_browser:
            webbrowser.open(url)
            
        return url
    
    def stop_server(self) -> None:
        """Stop the web server if it's running."""
        if self.server:
            self.server.shutdown()
            self.server.server_close()
            self.server = None
            self.server_thread = None
            
            # Clean up temporary directory
            if self.temp_dir and os.path.exists(self.temp_dir):
                shutil.rmtree(self.temp_dir)
                self.temp_dir = None
                
            logger.info("Trace viewer server stopped")
    
    def generate_report(self, trace_id: str, output_file: Optional[str] = None) -> Optional[str]:
        """
        Generate a static HTML report for a trace.
        
        Args:
            trace_id: ID of the trace
            output_file: Optional output file path (default: trace_id.html)
            
        Returns:
            output_path: Path to the generated report file or None if failed
        """
        trace = self.get_trace(trace_id)
        
        if not trace:
            logger.error(f"Trace not found: {trace_id}")
            return None
            
        # Default output file
        if not output_file:
            output_file = f"trace_{trace_id}.html"
            
        output_path = Path(output_file)
        
        try:
            # Generate HTML
            trace_data = {trace_id: trace}
            html_content = HTML_TEMPLATE.replace(
                "{trace_data_json}", json.dumps(trace_data)
            ).replace(
                "{trace_list_items}", ""  # Generated by JavaScript
            )
            
            # Write HTML to file
            with open(output_path, 'w') as f:
                f.write(html_content)
                
            logger.info(f"Generated trace report: {output_path}")
            return str(output_path)
                
        except Exception as e:
            logger.error(f"Error generating report for trace {trace_id}: {e}")
            return None
    
    def export_trace(self, trace_id: str, format: str = "json", 
                   output_file: Optional[str] = None) -> Optional[str]:
        """
        Export a trace to various formats (json, csv, etc).
        
        Args:
            trace_id: ID of the trace
            format: Export format ('json', 'csv', etc)
            output_file: Optional output file path
            
        Returns:
            output_path: Path to the exported file or None if failed
        """
        trace = self.get_trace(trace_id)
        
        if not trace:
            logger.error(f"Trace not found: {trace_id}")
            return None
            
        # Default output file
        if not output_file:
            output_file = f"trace_{trace_id}.{format}"
            
        output_path = Path(output_file)
        
        try:
            if format == "json":
                # Export to JSON
                with open(output_path, 'w') as f:
                    json.dump(trace, f, indent=2)
                    
            elif format == "csv":
                # Export to CSV - events only
                import csv
                
                with open(output_path, 'w', newline='') as f:
                    writer = csv.writer(f)
                    
                    # Write header
                    writer.writerow([
                        "event_id", "event_type", "component_id", 
                        "timestamp", "time_offset", "span_id", "sequence"
                    ])
                    
                    # Write events
                    start_time = trace.get("start_time", 0)
                    for event in trace.get("events", []):
                        time_offset = event.get("timestamp", 0) - start_time
                        writer.writerow([
                            event.get("event_id", ""),
                            event.get("event_type", ""),
                            event.get("component_id", ""),
                            event.get("timestamp", ""),
                            f"{time_offset:.6f}",
                            event.get("span_id", ""),
                            event.get("sequence", "")
                        ])
                        
            else:
                logger.error(f"Unsupported export format: {format}")
                return None
                
            logger.info(f"Exported trace to {output_path}")
            return str(output_path)
                
        except Exception as e:
            logger.error(f"Error exporting trace {trace_id}: {e}")
            return None
    
    def tail_trace(self, trace_id: str, 
                 event_limit: int = 10, 
                 refresh_interval: Optional[float] = None) -> None:
        """
        Tail a trace in real-time, showing new events as they arrive.
        
        Args:
            trace_id: ID of the trace to tail
            event_limit: Number of events to show
            refresh_interval: Seconds between refreshes (default: from config)
        """
        refresh_interval = refresh_interval or self.refresh_interval
        last_event_count = 0
        
        try:
            while True:
                trace = self.get_trace(trace_id)
                
                if not trace:
                    logger.error(f"Trace not found: {trace_id}")
                    return
                    
                events = trace.get("events", [])
                event_count = len(events)
                
                # Check if there are new events
                if event_count > last_event_count:
                    # Clear screen (platform-dependent)
                    os.system('cls' if os.name == 'nt' else 'clear')
                    
                    # Print trace info
                    status = trace.get("status", "unknown")
                    start_time = datetime.fromtimestamp(trace.get("start_time", 0))
                    duration = trace.get("duration", 0)
                    
                    print(f"Trace: {trace_id}")
                    print(f"Status: {status}")
                    print(f"Started: {start_time}")
                    print(f"Duration: {duration:.3f}s")
                    print(f"Events: {event_count}")
                    print("-" * 80)
                    
                    # Print recent events
                    recent_events = events[-event_limit:]
                    
                    for event in recent_events:
                        timestamp = event.get("timestamp", 0)
                        time_offset = timestamp - trace.get("start_time", 0)
                        event_type = event.get("event_type", "unknown")
                        component = event.get("component_id", "unknown")
                        
                        print(f"+{time_offset:.3f}s - {event_type} - {component}")
                        
                    last_event_count = event_count
                    
                # Check if trace is complete
                if status == "completed":
                    print("\nTrace completed.")
                    break
                    
                # Wait for next refresh
                time.sleep(refresh_interval)
                
        except KeyboardInterrupt:
            print("\nTailing stopped.")
            
    @staticmethod
    def run_cli():
        """
        Run the trace viewer as a command-line tool.
        """
        parser = argparse.ArgumentParser(description="Neuron Trace Viewer CLI")
        
        # Common arguments
        parser.add_argument("--log-dir", help="Directory containing trace logs")
        parser.add_argument("--debug", action="store_true", help="Enable debug logging")
        
        # Subcommands
        subparsers = parser.add_subparsers(dest="command", help="Command to run")
        
        # List command
        list_parser = subparsers.add_parser("list", help="List available traces")
        list_parser.add_argument("--limit", type=int, default=10, help="Maximum traces to show")
        list_parser.add_argument("--status", choices=["completed", "running", "error"], help="Filter by status")
        
        # Show command
        show_parser = subparsers.add_parser("show", help="Show details of a trace")
        show_parser.add_argument("trace_id", help="ID of the trace to show")
        
        # Server command
        server_parser = subparsers.add_parser("server", help="Start web server for visualization")
        server_parser.add_argument("--host", default="localhost", help="Server host")
        server_parser.add_argument("--port", type=int, default=8675, help="Server port")
        server_parser.add_argument("--no-browser", action="store_true", help="Don't open browser automatically")
        
        # Report command
        report_parser = subparsers.add_parser("report", help="Generate HTML report for a trace")
        report_parser.add_argument("trace_id", help="ID of the trace to report")
        report_parser.add_argument("--output", help="Output file path")
        
        # Export command
        export_parser = subparsers.add_parser("export", help="Export trace to various formats")
        export_parser.add_argument("trace_id", help="ID of the trace to export")
        export_parser.add_argument("--format", default="json", choices=["json", "csv"], help="Export format")
        export_parser.add_argument("--output", help="Output file path")
        
        # Tail command
        tail_parser = subparsers.add_parser("tail", help="Tail a trace in real-time")
        tail_parser.add_argument("trace_id", help="ID of the trace to tail")
        tail_parser.add_argument("--limit", type=int, default=10, help="Number of events to show")
        tail_parser.add_argument("--interval", type=float, default=1.0, help="Refresh interval in seconds")
        
        # Parse arguments
        args = parser.parse_args()
        
        # Configure viewer
        config = {}
        
        if args.log_dir:
            config["trace_log_dir"] = args.log_dir
            
        config["debug"] = args.debug
        
        viewer = TraceViewer(config)
        
        # Execute command
        if args.command == "list":
            traces = viewer.list_traces(max_count=args.limit, filter_status=args.status)
            
            if not traces:
                print("No traces found.")
                return
                
            print(f"Found {len(traces)} traces:")
            for trace in traces:
                trace_id = trace["trace_id"]
                status = trace["status"]
                start_time = datetime.fromtimestamp(trace["start_time"])
                event_count = trace["event_count"]
                
                print(f"{trace_id} - {status} - {start_time} - {event_count} events")
                
        elif args.command == "show":
            trace = viewer.get_trace(args.trace_id)
            
            if not trace:
                print(f"Trace not found: {args.trace_id}")
                return
                
            # Print basic info
            status = trace.get("status", "unknown")
            start_time = datetime.fromtimestamp(trace.get("start_time", 0))
            duration = trace.get("duration", 0)
            
            print(f"Trace: {args.trace_id}")
            print(f"Status: {status}")
            print(f"Started: {start_time}")
            print(f"Duration: {duration:.3f}s")
            print(f"Events: {len(trace.get('events', []))}")
            print(f"Spans: {len(trace.get('spans', []))}")
            
            # Print metadata
            metadata = trace.get("metadata", {})
            if metadata:
                print("\nMetadata:")
                for key, value in metadata.items():
                    print(f"  {key}: {value}")
                    
            # Print event summary
            event_types = {}
            for event in trace.get("events", []):
                event_type = event.get("event_type", "unknown")
                if event_type not in event_types:
                    event_types[event_type] = 0
                event_types[event_type] += 1
                
            if event_types:
                print("\nEvent Types:")
                for event_type, count in event_types.items():
                    print(f"  {event_type}: {count}")
                    
        elif args.command == "server":
            config["server_host"] = args.host
            config["server_port"] = args.port
            config["auto_open_browser"] = not args.no_browser
            
            viewer = TraceViewer(config)
            
            try:
                url = viewer.start_server()
                print(f"Trace viewer server started at {url}")
                print("Press Ctrl+C to stop the server.")
                
                # Keep the server running until interrupted
                while True:
                    time.sleep(1)
                    
            except KeyboardInterrupt:
                print("Stopping server...")
                viewer.stop_server()
                
        elif args.command == "report":
            output_file = args.output
            result = viewer.generate_report(args.trace_id, output_file)
            
            if result:
                print(f"Report generated: {result}")
            else:
                print(f"Failed to generate report for trace: {args.trace_id}")
                
        elif args.command == "export":
            output_file = args.output
            result = viewer.export_trace(args.trace_id, args.format, output_file)
            
            if result:
                print(f"Trace exported to: {result}")
            else:
                print(f"Failed to export trace: {args.trace_id}")
                
        elif args.command == "tail":
            viewer.tail_trace(args.trace_id, args.limit, args.interval)
            
        else:
            parser.print_help()

# Trace Viewer Summary
# -------------------
# The TraceViewer module provides tools for visualizing and analyzing execution
# traces generated by the TraceLogger component of the Neuron architecture.
#
# Key features:
#
# 1. Interactive Visualization:
#    - Web-based interface for exploring trace data
#    - Timeline views of execution events
#    - Hierarchical span visualization
#    - Filtering and search capabilities
#    - Real-time trace tailing
#
# 2. Trace Analysis:
#    - Statistical analysis of execution patterns
#    - Component activity breakdowns
#    - Performance metrics and bottleneck identification
#    - Error detection and root cause analysis
#    - Cross-trace comparison
#
# 3. Export Capabilities:
#    - Generate standalone HTML reports
#    - Export to various formats (JSON, CSV)
#    - Share and archive execution traces
#    - Documentation generation
#
# 4. Command-Line Interface:
#    - Fast access to trace information
#    - Scriptable trace analysis
#    - CI/CD integration capabilities
#    - Batch processing of trace data
#
# This module enables developers to debug, optimize, and understand the behavior of
# Neuron circuits by providing comprehensive visibility into execution paths,
# component interactions, and system performance.
