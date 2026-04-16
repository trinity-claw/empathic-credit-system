# CloudWalk Technical Case: The Empathic Credit System (ECS)

## Background
CloudWalk has developed groundbreaking technology that can sense and interpret people's emotions and thoughts in real‑time. This technology has been integrated into CloudWalk's mobile app, which is used by millions of customers. Your task is to design and implement a system that leverages this emotional data to offer and deploy personalized credit offers to users.

In addition to this fictional empathic technology, CloudWalk is a real fintech company that provides AI‑ and blockchain‑driven financial solutions to individuals and small businesses. Through its flagship brand InfinitePay, CloudWalk offers payment solutions such as card machines, bank accounts and various financial services for merchants and companies. Other products include Infinite Nitro for instant payouts, Payment Link for seamless online transactions, Supercobra for accounts receivable management and Infinite Tap for tap‑to‑pay payments. The company also offers AI‑driven lending via Infinite Cash and supports instant payments via PIX processing. These services provide context for why the user profile database should capture transaction history and financial interactions.

## The Software Engineer Challenge
### System Requirements
> #### System Architecture Diagram:
- Create a comprehensive system architecture diagram that illustrates the flow of data and interactions between different components of the Empathic Credit System.
- Start the diagram with the customers' brains as the initial data source, showcasing how their emotions and thoughts are captured and processed through the system.
- Include all major components such as the mobile app, data streams, APIs, databases, machine learning models, and any other elements you deem necessary.
- Clearly show the data flow and interactions between these components.
> #### Real-time Emotion Processing:
- Implement a listening system that captures a stream of emotional data from users.
- The content and structure of each message are not predefined. You have the freedom to design the data model as you see fit for this system.
> #### Machine Learning Integration:
- Integrate a pre-trained machine learning model into your system. You do not need to build this model yourself.
- Assume the model exists as a black box that accepts certain features and returns a credit risk score. For the purposes of this exercise, you can mock the actual model call with a function that returns a random risk score.
- Your task here is to:
1) Design the interface for calling this pre-trained model.
2) Determine which features from your processed emotional and financial data should be passed to the model.
3) Integrate the model's output (credit risk score) into your credit limit calculation process.
> #### Credit Limit API:
- Create a RESTful API endpoint that calculates and returns
1) The ML model result. If the user was approved for a credit line
2) The credit limit and interest rate
3) Credit type (e.g., Short-Term, Long-Term)
- The endpoint should accept relevant parameters and return the calculated credit limit and interest rate.
> #### User Profile Database:
- Design and implement a database schema to store user profiles, including their transaction history, current credit limits, and emotional data.
- Use a relational database of your choice.
> #### Credit Limit Deployment and Notification:
- Design and implement a mechanism to apply approved credit offers to user accounts. Once a credit offer is accepted, your system should update the user’s profile in the database and notify the user via the mobile app.
- Rather than performing this work synchronously in the request–response cycle, build an asynchronous process or background worker (for example, using a message queue or task queue) that listens for credit‑approval events and applies the updates. This reflects CloudWalk’s real‑world use of event‑driven, micro‑service architectures to keep interactions fast, fair and traceable.
> #### Observability and Logging:
- Implement structured logging and write logs to standard output (STDOUT). Your logs should contain enough context (e.g., request identifiers, user IDs) to trace issues across services. Avoid writing logfiles in the application; treat logs as an event stream so they can be aggregated externally.
- Expose a basic /healthz (or similar) endpoint for health‑check probes and service monitoring. You may optionally add metrics or tracing instrumentation.
> #### Configuration and Security:
- Store configuration values such as database URLs, credentials and external endpoints in environment variables rather than hard‑coding them or checking them into source control.
- Protect your APIs with an authentication mechanism of your choice (for example, HTTP Basic Auth or token‑based authentication). Ensure secrets are handled securely.
- Use appropriate HTTP status codes for success and error responses
> #### Database Schema and Queries:
- Design a relational schema for users, transactions, credit limits and emotional events. Include primary/foreign keys and indexes where appropriate to ensure efficient queries.
- Provide at least two example SQL queries in your documentation—for example, retrieving all emotional events for a user in the last week or identifying high‑risk customers based on credit score thresholds.
> #### Real‑Time Data Streaming:
- Implement a mechanism to consume and process emotional data in real time. You may choose a streaming technology such as Kafka, RabbitMQ or Pub/Sub, or any other method appropriate for your implementation.
- Ensure that your system can handle concurrent messages and recover gracefully from transient errors.
> #### Data Privacy and Ethics:
- Include a brief section in your documentation outlining how you would handle sensitive emotional data. Consider encryption at rest/in transit, pseudonymisation/anonymisation techniques and compliance with data protection regulations (e.g., LGPD). Explain any trade‑offs or assumptions you make.

### Technical Requirements
- Use Python for the backend implementation.
- Implement proper error handling and logging throughout the system.
- Use Docker and docker-compose to containerize your application and its dependencies.
- Implement basic authentication for the API endpoints.
- Provide clear documentation on how to set up and run your solution.

### Optional Enhancements
- Write tests for critical components.
- Implement a simple frontend dashboard to visualize emotional trends and credit limit distributions.
- Design a circuit breaker pattern to handle potential failures in the machine learning model service.
- Propose a strategy for handling data privacy concerns related to emotional data processing.
- Emotional Data Analysis: Provide some insight on trends and key take aways of the emotions captured

## Evaluation Criteria
Your solution will be evaluated based on:
- Code quality and organization
- System design and architecture
- Handling of various technical components (data streaming, databases, API design, ML integration)
- Error handling and edge case consideration
- Documentation and ease of setup
- Bonus points for additional features or well-reasoned design choices

## Submission Guidelines
- Provide your solution in a GitHub repository.
- Include a README.md with setup instructions and any assumptions you made.
- Prepare a brief presentation (30 minutes) explaining your design choices and walking through key parts of your implementation.

## *DISCLAIMER*
The Empathic Credit System (ECS) described in this case study is entirely fictional. This concept was created solely for the purpose of this exercise and does not represent any real-world technology or system. The idea of using emotional data for credit decisions is purely hypothetical and is meant to stimulate creative thinking and analysis within the context of this technical case.

Good luck!