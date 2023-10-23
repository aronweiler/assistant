SINGLE_SHOT_DESIGN_DECISION_TEMPLATE = """Imagine you're crafting the blueprint for a groundbreaking project that will revolutionize the industry! Your design decisions will be the cornerstone of this innovation. Each choice you make is a step towards excellence, ensuring the final product exceeds all expectations. Let your creativity and expertise shine as you transform requirements into a masterpiece of engineering brilliance!

You are designing a new system for a {project_name}. We have identified the following user needs:

{user_needs}

From those user needs, we have extracted the following (subset of the overall) requirements:

ID: {requirement_id}, Requirement: {requirement}

I need you to make design decisions for this requirement, such as component breakdown, programming language selection, third-party component selection, etc., taking into account the following design decisions that have already been made:

{existing_design_decisions}

You should follow these steps when making your design decision:
    
    1. Understand the Requirement:
        Read and analyze the requirement document thoroughly.
        Identify the key objectives, functionalities, and constraints.
    
    2. Define Functional Components:
        Break down the requirement into smaller functional components or modules.
        Each component should represent a specific aspect of the overall requirement.

    3. Document Design Decisions:
        Clearly document the rationale behind each design decision.
        Include considerations, trade-offs, and any potential risks associated with the decision.

Your output should follow this JSON format:

{{
  "requirement_id": "requirement id", "Components": [{{"name": "component name", "decision": "your recommendation", "details": "explanation of your recommendation"}}, ...]
}}

For example:

{{
  "requirement_id": "17", "Components": [{{"name": "Database", "decision" : "SQLite", "details": "SQLite is a lightweight option suitable for single-user applications."}}, {{"name": "Language", "decision": "C# (WPF)", "details": "C# with WPF provides a quick and easy way to create Windows-based applications."}}, ]
}}

AI: Sure, here is the design decision in JSON format:
"""

DESIGN_DECISION_TEMPLATE = """Imagine you're crafting the blueprint for a groundbreaking project that will revolutionize the industry! Your design decisions will be the cornerstone of this innovation. Each choice you make is a step towards excellence, ensuring the final product exceeds all expectations. Let your creativity and expertise shine as you transform the user's input into a masterpiece of engineering brilliance!

The system has the following requirements:
{requirements}

From those requirements, we have identified the following architectural component, and some of its details:
{component}

Additionally, there may be some interfaces related to these components (note: this could be empty):
{interfaces}

I need you to make design decisions for this component, including: technology stack, programming language, third-party component selection, etc., taking into account the following design decisions that have already been made:

{existing_design_decisions}

You should follow these steps when making your design decision:
    
    1. Understand the Requirements:
        Read and analyze the requirements thoroughly.
        Identify the key objectives, functionalities, and constraints.    

    2. Understand the Interfaces:
        Read and analyze the interfaces thoroughly.
        Identify the key objectives, functionalities, and constraints.

    2. Document Design Decisions:
        Make your design decisions for each component.
        Clearly document the rationale behind each design decision.
        Include considerations, trade-offs, and any potential risks associated with the decision.
        Ensure that the design decisions are consistent with the requirements and interfaces.

Your output should follow this JSON format:

{{	
	"Component Designs": [
		{{
			"component": "component name",
			"decision": "your design decision",
			"details": "details and explanation of your design decision"
		}}
	]
}}

For example:

{{	
	"Component Designs": [
		{{
			"component": "Kiosk Interface",
			"decision": "C# (WPF)",
			"details": "C# with WPF provides a quick and easy way to create Windows-based kiosk applications."
		}},
		{{
			"component": "Kiosk Interface",
			"decision": "ModernWPF UI Library",
			"details": "The ModernWPF UI Library allows us to style the buttons, and other controls using a modern UI look and feel, which will add to the user experience."
		}}
	]
}}

AI: Sure, here are the design decisions in JSON format:
"""

COMPONENT_DECOMPOSITION_TEMPLATE = """Imagine you're crafting the blueprint for a groundbreaking project that will revolutionize the industry! Your design decisions will be the cornerstone of this innovation. Each choice you make is a step towards excellence, ensuring the final product exceeds all expectations. Let your creativity and expertise shine as you transform requirements into a masterpiece of engineering brilliance!

Given the following list of user needs, requirements, and existing design decisions, decompose the described system down into architectural components.  Provide a comprehensive description of the architectural components you create and their roles in the system design. 

User Needs:
{user_needs}

Requirements:
{requirements}

Existing Design Decisions:
{existing_design_decisions}

Please create the components needed to fulfill these requirements, and include the following details for each component:

- Name: The component name
- Purpose: Detailed description of the purpose and functionality
- Inputs: Specify the types of data or information that flow into the component
- Outputs: Specify the types of data or information that flow out of the component
- Interactions: Describe each interaction between this component and other components in the system
- Data handling: Explain how the component processes, stores, and manages data
- Dependencies: Identify any dependencies between components, specifying which components each component relies on

Please ensure that the descriptions of the components you create provides a clear understanding of how each component contributes to the overall system architecture, guiding the development process effectively and efficiently.

Your output should follow this JSON format:

{{
	"Components": [
		{{
			"name": "component name",
			"purpose": "Detailed description of the purpose and functionality",
			"inputs": [
				"input description",
				"input description"
			],
			"outputs": [
				"output description",
				"output description"
			],
			"interactions": [
				{{
					"interacts_with": "name of the component this component interacts with",
					"description": "detailed description of the interaction"
				}}
			],
            "data_handling": [
				{{
					"data_name": "name of the data",
                    "data_type": "type of the data",
					"description": "detailed description of the data",                    
				}}
			],
			"dependencies": [
				{{
					"dependency_name": "name of the component this component depends on",
					"description": "detailed description of the dependency"
				}}
			]
		}}
	]
}}

AI: Sure, here is the description of the architectural components and their roles (in JSON format):
"""

KEY_SYSTEM_INTERFACES_TEMPLATE = """Imagine you're crafting the blueprint for a groundbreaking project that will revolutionize the industry! Your design decisions will be the cornerstone of this innovation. Each choice you make is a step towards excellence, ensuring the final product exceeds all expectations. Let your creativity and expertise shine as you transform requirements into a masterpiece of engineering brilliance!

Given the following list of components in a system, identify the key system interfaces.  Provide a comprehensive description of the key system interfaces you identify and their roles in the system design.

Components:
{components}

Detail the interfaces (e.g., APIs, protocols) that the component exposes for interaction with other parts of the system.  For each interface, provide the following details:

- Name: The interface name
- Component name: The name of the component the interface belongs to
- Purpose: Detailed description of the purpose of the interface (e.g. how it is to be used, what it is used for, etc.)
- Inputs: Specify the types of data or information that flow into the interface
- Outputs: Specify the types of data or information that flow out of the interface

{{
	"Interfaces": [
		{{
			"name": "interface name",
            "component_name": "name of the component the interface belongs to",
			"purpose": "Detailed description of the interface",
			"inputs": [
                {{
                    "input_type": "type of input",
                    "description": "input description"
			    }}
            ],
			"outputs": [
                {{
                    "output_type": "type of output",
                    "description": "output description"
			    }}
            ],			
		}}
	]
}}

AI: Sure, here are the key interfaces (in JSON format):
"""

# Additional items that should be in the architecture (we should be iterating over this list):
# - Data Handling:
# - Interfaces:
# - Scalability Considerations:
# - Performance Characteristics:
# - Security Measures:
# - Error Handling:
# - Resilience and Fault Tolerance:
# - Compliance with Standards:
# - Technology Stack:
# - Hardware and Software Requirements:
# - Lifecycle Considerations:
# - Documentation and Support:
# - Integration Points:
# - Constraints and Limitations:















