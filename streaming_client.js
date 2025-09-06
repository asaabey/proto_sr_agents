// Example: Consuming the Streaming API with JavaScript
// This shows how to connect to the streaming endpoints and handle events

class StreamingReviewClient {
    constructor(baseUrl = 'http://localhost:8000') {
        this.baseUrl = baseUrl;
        this.eventSource = null;
    }

    // Stream analysis from JSON manuscript data
    async streamAnalysis(manuscriptData) {
        const response = await fetch(`${this.baseUrl}/review/start/stream`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify(manuscriptData)
        });

        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }

        return this.handleStreamingResponse(response);
    }

    // Stream analysis from file upload
    async streamFileAnalysis(file) {
        const formData = new FormData();
        formData.append('file', file);

        const response = await fetch(`${this.baseUrl}/review/upload/stream`, {
            method: 'POST',
            body: formData
        });

        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }

        return this.handleStreamingResponse(response);
    }

    // Handle the streaming response
    async handleStreamingResponse(response) {
        const reader = response.body.getReader();
        const decoder = new TextDecoder();

        const events = [];

        while (true) {
            const { done, value } = await reader.read();

            if (done) {
                break;
            }

            const chunk = decoder.decode(value);
            const lines = chunk.split('\n');

            for (const line of lines) {
                if (line.startsWith('data: ')) {
                    try {
                        const eventData = JSON.parse(line.substring(6));
                        events.push(eventData);

                        // Call event handler if provided
                        if (this.onEvent) {
                            this.onEvent(eventData);
                        }

                        // Log progress
                        console.log(`[${eventData.event_type}] ${eventData.message}`);

                    } catch (e) {
                        console.error('Error parsing event data:', e);
                    }
                }
            }
        }

        return events;
    }

    // Set event handler
    onEvent(callback) {
        this.onEvent = callback;
    }

    // Stop streaming
    stop() {
        if (this.eventSource) {
            this.eventSource.close();
            this.eventSource = null;
        }
    }
}

// Example usage:
async function exampleUsage() {
    const client = new StreamingReviewClient();

    // Handle streaming events
    client.onEvent = (event) => {
        switch (event.event_type) {
            case 'agent_start':
                console.log(`🚀 Starting ${event.agent}: ${event.message}`);
                break;
            case 'agent_complete':
                console.log(`✅ Completed ${event.agent}: ${event.message}`);
                if (event.data) {
                    console.log(`   Found ${event.data.issues_found} issues`);
                }
                break;
            case 'complete':
                console.log(`🎉 Analysis complete!`);
                if (event.data) {
                    console.log(`   Total issues: ${event.data.total_issues}`);
                    console.log(`   LLM calls: ${event.data.llm_calls}`);
                }
                break;
            case 'error':
                console.error(`❌ Error: ${event.message}`);
                break;
            default:
                console.log(`📝 ${event.message}`);
        }
    };

    try {
        // Example 1: Stream analysis with JSON data
        const manuscriptData = {
            manuscript_id: "example_001",
            title: "Effect of Exercise on Depression",
            question: {
                framework: "PICO",
                population: "Adults with depression",
                intervention: "Exercise therapy",
                comparator: "Standard care",
                outcomes: ["Depression symptoms", "Quality of life"]
            },
            search: [{
                db: "PubMed",
                strategy: "exercise AND depression",
                dates: "2020-2024"
            }],
            flow: {
                identified: 1000,
                screened: 800,
                fulltext: 50,
                included: 10
            },
            included_studies: [
                {
                    study_id: "study1",
                    design: "RCT",
                    n_total: 100,
                    outcomes: [{
                        name: "Depression score",
                        effect_metric: "MD",
                        effect: -5.2,
                        var: 2.1
                    }]
                }
            ]
        };

        console.log('Starting streaming analysis...');
        const events = await client.streamAnalysis(manuscriptData);
        console.log(`Received ${events.length} events`);

    } catch (error) {
        console.error('Streaming failed:', error);
    }
}

// Export for use in other modules
if (typeof module !== 'undefined' && module.exports) {
    module.exports = StreamingReviewClient;
}

// For browser usage, attach to window
if (typeof window !== 'undefined') {
    window.StreamingReviewClient = StreamingReviewClient;
}
