## ADDED Requirements

### Requirement: System SHALL record structured AI execution trace runs and steps
The system SHALL record structured AI execution traces for assistant, Agent, tool, generation, review, and pipeline executions. Each trace run MUST group related steps under a stable run identifier, and each step MUST include timestamp, step name, step kind, status, input summary, output summary, error details when failed, and associated knowledge sources when available.

#### Scenario: Tool execution creates trace step
- **WHEN** the assistant or an Agent starts a tool call during a run
- **THEN** the system MUST create a trace step with status `running`
- **AND** the step MUST include the run identifier, tool name, step kind, timestamp, and summarized input parameters

#### Scenario: Tool execution completes trace step
- **WHEN** the tool call finishes successfully
- **THEN** the system MUST update the matching trace step to a successful terminal status
- **AND** the step MUST include an output summary derived from the tool result

#### Scenario: Tool execution fails
- **WHEN** the tool call raises an error or returns a failed result
- **THEN** the system MUST update the matching trace step to a failed terminal status
- **AND** the step MUST expose explicit error information instead of silently omitting the failed step

### Requirement: System SHALL persist or retain traces through an explicit storage mode
The system SHALL provide a trace repository with an explicit storage mode. The implementation MUST support an in-memory mode for temporary retention and MAY support SQLite persistence for local replay. The selected mode MUST be explicit and MUST NOT silently fall back to another mode when storage fails.

#### Scenario: In-memory trace mode is enabled
- **WHEN** the trace repository is configured to use in-memory storage
- **THEN** newly recorded runs and steps MUST be available through trace query APIs while the process remains alive
- **AND** the system MUST treat process restart data loss as an explicit limitation of that mode

#### Scenario: SQLite trace mode fails to write
- **WHEN** SQLite trace storage is configured and a trace write fails
- **THEN** the system MUST surface the trace write failure explicitly
- **AND** the system MUST NOT report a fabricated successful trace write

### Requirement: System SHALL expose trace data to the frontend
The system SHALL expose trace runs, steps, and sources through backend APIs suitable for frontend polling or real-time updates. The API MUST support querying recent traces by project, card, or run identifier.

#### Scenario: Frontend requests recent traces for current card
- **WHEN** the frontend requests recent execution traces for a project and card
- **THEN** the backend MUST return trace runs and ordered steps relevant to that project and card
- **AND** the response MUST include source references attached to each step when available

#### Scenario: Frontend tracks an active run
- **WHEN** an assistant, Agent, generation, or review run is active
- **THEN** the frontend MUST be able to retrieve the active run identifier or receive trace updates associated with that run
- **AND** updates MUST preserve chronological step order

### Requirement: Tool and pipeline execution SHALL emit trace-compatible metadata
The system SHALL integrate trace recording with standardized tool and pipeline execution events. Tool start/end events and pipeline step events MUST be convertible into trace steps without tool-specific UI code for every individual tool.

#### Scenario: Standard tool event is recorded
- **WHEN** the tool pipeline emits a `tool_start` or `tool_end` event
- **THEN** the trace layer MUST convert that event into a corresponding trace step update
- **AND** the conversion MUST include tool name, call id when available, status, input summary, output summary, and policy metadata when available

#### Scenario: Schema-aware display metadata is available
- **WHEN** a tool definition includes input or output schema metadata
- **THEN** the trace layer MUST preserve enough schema metadata for the frontend to render a readable step card
- **AND** the frontend MUST NOT require hardcoded display logic for each supported tool

### Requirement: Trace steps SHALL include knowledge source attribution
The system SHALL support explicit source attribution for knowledge, context, card, and graph references used during AI execution. Each source attribution MUST include source type, source reference, readable label, preview content, and jump target when available.

#### Scenario: Knowledge source is referenced by a tool
- **WHEN** a tool result includes `knowledge_sources`, `sources`, or `references`
- **THEN** the trace layer MUST normalize those values into structured source attribution records
- **AND** the frontend MUST be able to display the source label and preview in the trace panel

#### Scenario: Source points to a card
- **WHEN** a source attribution references a card
- **THEN** the source record MUST include enough jump target data for the frontend to navigate to that card
- **AND** the trace panel MUST present the source as a clickable reference when navigation data is available

### Requirement: Frontend SHALL provide a context insight panel
The frontend SHALL provide a context insight panel in the creative workspace. The panel MUST display AI execution traces as a timeline or ordered step cards and MUST distinguish tool calls, pipeline steps, context references, knowledge references, and errors.

#### Scenario: User opens creative workspace after an AI run
- **WHEN** a user opens the creative workspace for a card with recent AI execution traces
- **THEN** the context insight panel MUST show recent trace runs and their ordered steps
- **AND** each step MUST display readable status, step name, input summary, output summary, and sources when present

#### Scenario: Active AI run emits new trace step
- **WHEN** an active AI run records a new trace step
- **THEN** the context insight panel MUST update to show the new step through polling or real-time updates
- **AND** the user MUST be able to distinguish running, successful, and failed steps

#### Scenario: Trace source is clickable
- **WHEN** a trace step includes a source with a jump target
- **THEN** the context insight panel MUST render that source as a clickable item
- **AND** activating it MUST navigate to or reveal the referenced card, knowledge item, or graph entity when supported

### Requirement: System SHALL support output-to-source span metadata without requiring it for all outputs
The system SHALL define optional span metadata that can associate output text ranges with trace sources. The UI MAY use this metadata to highlight output text and show source details on hover, but the absence of span metadata MUST NOT prevent trace source display.

#### Scenario: Output span metadata is available
- **WHEN** an AI output includes source span metadata
- **THEN** the frontend MUST be able to highlight the referenced output range
- **AND** hovering the highlighted text MUST show the associated source details

#### Scenario: Output span metadata is unavailable
- **WHEN** an AI output has source attribution but no character range metadata
- **THEN** the frontend MUST still display source attribution in the context insight panel
- **AND** the system MUST NOT fabricate character-level highlights

### Requirement: System SHALL NOT expose hidden model reasoning as execution trace
The system SHALL NOT record or display hidden model reasoning, private chain-of-thought, or provider-internal reasoning as execution trace. Execution trace MUST be limited to observable system events such as tool calls, pipeline steps, context assembly, knowledge references, visible model messages, and explicit errors.

#### Scenario: Model provider returns internal reasoning metadata
- **WHEN** model output includes hidden or provider-internal reasoning metadata
- **THEN** the trace layer MUST NOT persist that hidden reasoning as a user-visible trace step
- **AND** the frontend MUST NOT label trace data as the model's private thought process

#### Scenario: Visible tool call is available
- **WHEN** the model requests a tool call or the system executes a pipeline step
- **THEN** the trace layer MAY record that observable event as execution trace
- **AND** the trace MUST describe the system action rather than claiming to reveal hidden reasoning
