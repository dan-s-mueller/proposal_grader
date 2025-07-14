# 2025 SBIR Ignite AI AMA FAQ

## NASA SBIR Ignite 2025  
**Audience Q&A: AI-Powered Design for Multidisciplinary Space Hardware**  
**Subtopic I02.01: Multidisciplinary Space Hardware Design Automation Leveraging AI Techniques**

---

### Q: Can you elaborate with examples where the commercial and NASA overlap exists for the AI segment, for AI segment applications in hardware?  
The text-to-spaceship vision aligns commercial tools around a broader vision, and commercial tools are already being developed and used in this area. Startups and incumbents both work on this, with startups typically moving faster. Specific company names are withheld to avoid favoritism.

---

### Q: What TRL should the AI be? What are you looking for in terms of stage development / maturity?  
Looking for innovative, good ideas that can be rapidly developed, typically starting at a lower TRL around 3 (not 6 or above). Focus is on early-stage, innovative development.

---

### Q: Does TRL 6+ mean some sort of flight testing?  
Per NASA standards, a TRL 6 demonstration should be in a relevant environment, ground or space. At TRL 6, an appropriate environment simulating operational conditions is expected.

---

### Q: What kind of outcome or demonstration is expected at the end of Phase One? The topic description is wide open, so some clarity would be helpful where possible.  
A demonstration powerful enough to convince skeptics that automating design (e.g., avionics, brackets, electronics) is possible. The demonstration should show an automated design output with value, even if it does not solve all edge cases. It should be a simple application that can grow more generic over time.

---

### Q: How do you see the current state-of-the-art commercial spacecraft design tools changing? Do you believe in the plug-in approach or a complete redesign of tools (e.g., SolidWorks for AI versus an agent working with SolidWorks)?  
Many current tools have APIs but use older CPU-based underlying computational engines and are thus slower. Tools without AI integration will likely see less use over time. The agentic approach allows easier swapping of tools, promoting use of newer tools validated with existing data sets. This reduces vendor lock-in and accelerates engineering companies that adopt these tools.

---

### Q: Is implicit usage of large language models (LLMs) allowed? Do the underlying models need to be housed offline (due to ITAR restrictions, for example)?  
Yes, implicit usage of LLMs is allowed. Use of APIs must comply with ITAR laws (e.g., do not use Deep Seek). Access to major commercial models like Claude, OpenAI, some Lama models, and AWS cloud are secured and allowed.

---

### Q: Are there required output or interoperability standards (e.g., OML, MBSE, STEP)?  
No mandatory standards, but use of open, interoperable formats is strongly encouraged over proprietary ones.

---

### Q: Is AI-driven text-to-circuit or chip layout design within scope?  
Yes, these areas are of interest and fall under hardware design automation relevant to NASA applications.

---

### Q: Will NASA provide sample data, digital artifacts, or templates?  
No comprehensive data sets are currently ready. Publicly available data should be used. Efforts to create public datasets and define schemas are ongoing.

---

### Q: Can a wearable interface be used to facilitate speech-to-text or gesture-to-text from which System Requirements Specification and system design documents are derived?  
Yes, incorporating XR or 3D input like gesture or speech is a valuable and encouraged approach.

---

### Q: Why not use Deep Seek? Are Deep Seek and other AI tools essentially the same cost?  
The choice depends on the AI model integration and compliance. The prompts are often specific to AI models used, and internal deployment requires API endpoints that must comply with regulations, which excludes Deep Seek.

---

### Q: What is NASA Luna and can it be used in this topic area?  
NASA Luna is a secure, collaborative data platform used internally at NASA. Its use is encouraged where relevant and appropriate.

---

### Q: Does NASA have specific AI/ML capability like object detection, classification, characterization?  
Those are part of AI for autonomy, which is different from AI for hardware (the current focus).

---

### Q: Are you looking for test-time compute functionality?  
Yes, test-time computation (letting models "think" during use) is encouraged.

---

### Q: Are there any security classifications for LLMs?  
Mostly internal; frontier models are hosted internally by NASA.

---

### Q: What are the biggest challenges NASA faces in multidisciplinary space hardware design automation today?  
The biggest challenges are:  
(1) Finding discipline experts that also have the knowledge and interest to apply AI to their field  
(2) Moving from legacy CPU-based, locally run, mouse-and-keyboard engineering tools to GPU-based, cloud native, API accessible tools

---

### Q: Are you looking for 3rd wave AI capability as compared to second wave?  
Either, as applicable.

---

### Q: For AI, does it have to be hardware design focused or can this be software related?  
We are looking for solutions that ultimately lead to automating hardware designs.

---

### Q: How fast is the current end-to-end automated design loop (re: topic I02.01 lists needed for at least 5× faster)?  
We are looking for solutions 5× faster compared to traditional non-automated approaches.

---

### Q: What are the current NASA initiatives in AI?  
NASA’s current initiatives span the breadth of its activities and are too numerous to list. Regarding AI-for-hardware, the AMA recording is a good source of information.

---

### Q: Are you only targeting design or are other parts of the product development lifecycle such as quality and test on topic?  
This topic is focused on design.
