IDENTIFY_VULNERABLE_COMPONENT_PROMPT = """
Identify the vulnerable component(s) and/or system(s) in the following vulnerability data.  Return only the description of the vulnerable components and/or systems.

--- VULNERABILITY DATA ---
{vulnerability_data}
--- VULNERABILITY DATA ---

AI: Sure, I can do that.  Here's the description of the vulnerable component(s) and/or system(s) in the vulnerability data:
"""

CVSS_INSTRUCT_PROMPT = """You are a security AI tasked with creating a CVSS score for a possible vulnerability.

The vulnerable component(s) have been identified as: {vulnerable_component}

Pay close attention to the following instructions for determining each metric of the CVSS vector string.

- Use the following information to evaluate the VULNERABILITY DATA to arrive at a CVSS Evaluation, including Base Metric Group CVSS 3.1 Vector String and evaluation explanations (cite detailed source data in your explanation) for each metric.
    - When scoring Base metrics, it should be assumed that the attacker has advanced knowledge of the weaknesses of the target system, including general configuration and default defense mechanisms (e.g., built-in firewalls, rate limits, traffic policing). For example, exploiting a vulnerability that results in repeatable, deterministic success should still be considered a Low value for Attack Complexity, independent of the attacker's knowledge or capabilities.
        Attack Vector (AV) represents how the vulnerability can be exploited, the default value is 'N'.
        If the vulnerability does not require any special conditions to be exploited, assign the value 'N' (Network).
        If the vulnerable component is bound to the network stack and the set of possible attackers extends beyond the other options listed below, up to and including the entire Internet, or if an attack can be launched over a wide area network or from outside the logically adjacent administrative network domain, assign the value 'N' (Network).
        If the vulnerable component requires the attacker to be in close physical proximity, but not physically interact with the system, or is bound to the network stack, but the attack is limited at the protocol level to a logically adjacent topology (e.g., Bluetooth, IEEE 802.11, RF, Zigbee, NFC, etc.) or logical (e.g., local IP subnet) network, or from within a secure or otherwise limited administrative domain (e.g., MPLS, secure VPN to an administrative network zone), assign the value 'A' (Adjacent Network).
        If the vulnerable component is not bound to the network stack and the attacker's path is via read/write/execute capabilities, assign the value 'L' (Local).
        If the vulnerability requires requires the attacker to physically touch or manipulate the vulnerable component, assign the value 'P' (Physical).

        Attack Complexity (AC) describes the conditions outside of the attacker's control that must exist in order to exploit the vulnerability, the default value is 'L'.        
        If the vulnerability does not contain specialized access conditions or extenuating circumstances, assign the value 'L' (Low).
        If the vulnerability depends on conditions beyond the attacker's control, i.e. a successful attack cannot be accomplished at will, but requires the attacker to invest in some measurable amount of effort in preparation or execution against the vulnerable component before a successful attack can be expected, assign the value 'H' (High).

        Privileges Required (PR) describes the privileges an attacker must possess, such as user account access, kernel access, access to a VM, PIN code, etc., before successfully exploiting the vulnerability, the default value is 'N'.
        If the attacker is anonymous, unauthorized, or does not require any legitimate access to the vulnerable system to carry out an attack, assign the value 'N' (None).
        If the attacker requires privileges that provide basic user capabilities (such as a user account), or an attack can be performed with low privileges (e.g. access to only non-sensitive resources), assign the value 'L' (Low).
        If the attacker requires privileges that provide significant control over the vulnerable component (such as an administrative account, or OS kernel access), assign the value 'H' (High).

        User Interaction (UI) represents the level of user (not attacker) interaction required to exploit the vulnerability, the default value is 'N'.
        If no user interaction is required to exploit the vulnerability, assign the value 'N' (None).
        If some form of user interaction is needed, to exploit the vulnerability, assign the value 'R' (Required).

        Scope (S) represents the impact of a successful exploit on the system's component or other components, the default value is 'U'.
        If the data does not mention, or does not include enough information to determine the scope, assign the default value 'U' (Unchanged).
        If the vulnerability's impact is limited to the vulnerable component (e.g., the target application or device), assign the value 'U' (Unchanged).
        If a successful exploit can impact components beyond the vulnerable component (e.g., other software applications or the underlying operating system), assign the value 'C' (Changed).

        Confidentiality (C), Integrity (I), and Availability (A):
        C, I, and A represent the impact on each of these security aspects when the vulnerability is exploited, the default value is 'H'.
        If the data does not mention, or does not include enough information to determine the impact to Confidentiality, Integrity, or Availability, assign the default value 'H' (High)
        If there is no impact on the specific security aspect, assign the value 'N' (None).
        If there is partial impact, for example:
            - There is some loss of confidentiality. Access to some restricted information is obtained, but the attacker does not have control over what information is obtained, or the amount or kind of loss is limited. The information disclosure does not cause a direct, serious loss to the impacted component.
            - Modification of data is possible, but the attacker does not have control over the consequence of a modification, or the amount of modification is limited. The data modification does not have a direct, serious impact on the impacted component.
            - Performance is reduced or there are interruptions in resource availability. Even if repeated exploitation of the vulnerability is possible, the attacker does not have the ability to completely deny service to legitimate users. The resources in the impacted component are either partially available all of the time, or fully available only some of the time, but overall there is no direct, serious consequence to the impacted component.
        assign the value 'L' (Low).
        If there is complete impact or a total loss, for example:
            - There is a total loss of confidentiality, resulting in all resources within the impacted component being divulged to the attacker. Alternatively, access to only some restricted information is obtained, but the disclosed information presents a direct, serious impact.
            - There is a total loss of integrity, resulting in the attacker being able to modify any/all files within the impacted component. Alternatively, only some files can be modified, but malicious modification would present a direct, serious consequence to the impacted component.
            - There is a total loss of availability, resulting in the attacker being able to fully deny access to resources in the impacted component, or the attacker has the ability to deny some availability, but the loss of availability presents a direct, serious consequence to the impacted component
        assign the value 'H' (High).
    - Assume that all preconditions for the vulnerability to exist are met, and that the attacker has all of the skills and equipment necessary to exploit the vulnerability.
    - DO NOT INCLUDE SPECIAL SKILLS OR EQUIPMENT REQUIRED TO EXPLOIT THE VULNERABILITY IN YOUR EVALUATION!
    - Prepend your evaluation with a description of the vulnerable component.
    - Assign the corresponding option value to each metric.
- IMPORTANT: If the data does not contain enough information to determine a metric's value, select the default value and explain why you selected it in your response.
- Don't forget to prefix the CVSS vector with 'CVSS:3.1/'

--- VULNERABILITY DATA ---
{vulnerability_data}
--- VULNERABILITY DATA ---

Always preface your detailed explanation of the vulnerability with the CVSS vector string (in a Markdown code block) corresponding to the evaluation you arrived at. (e.g. `CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:H/A:H`)

AI: Sure, I can do that.  Here's the CVSS vector string for the vulnerability in a Markdown code block, along with my detailed explanation of each metric:
"""