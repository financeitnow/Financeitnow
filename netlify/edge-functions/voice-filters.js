export default async function handler(request) {
  if (request.method !== 'POST') {
    return new Response(JSON.stringify({ error: 'Method not allowed' }), {
      status: 405,
      headers: { 'Content-Type': 'application/json' }
    });
  }

  let transcript, history;
  try {
    const body = await request.json();
    transcript = body.transcript;
    history = Array.isArray(body.history) ? body.history.slice(-6) : [];
  } catch {
    return new Response(JSON.stringify({ error: 'Invalid request body' }), {
      status: 400,
      headers: { 'Content-Type': 'application/json' }
    });
  }

  if (!transcript || typeof transcript !== 'string' || transcript.trim().length === 0) {
    return new Response(JSON.stringify({ error: 'Empty transcript' }), {
      status: 400,
      headers: { 'Content-Type': 'application/json' }
    });
  }

  // Sanitise - only plain text, max 500 chars to prevent prompt injection / abuse
  const sanitised = transcript.trim().replace(/[<>]/g, '').slice(0, 500);

  const apiKey = Deno.env.get('GROQ_API_KEY');
  if (!apiKey) {
    return new Response(JSON.stringify({ error: 'service_unavailable' }), {
      status: 503,
      headers: { 'Content-Type': 'application/json' }
    });
  }

  const systemPrompt = `You are Alex, a friendly and professional UK car sales agent at Finance it Now.
You help customers find their perfect car through a natural phone conversation.
Based on the customer's message, extract car filter values AND generate a warm spoken response.

Return ONLY a valid JSON object — no markdown, no explanation, just raw JSON:

{
  "make": string or null,
  "model": string or null,
  "minPrice": number or null,
  "maxPrice": number or null,
  "minMileage": number or null,
  "maxMileage": number or null,
  "yearFrom": number or null,
  "yearTo": number or null,
  "transmission": "Automatic" | "Manual" | null,
  "fuelType": "Petrol" | "Diesel" | "Electric" | "Hybrid" | null,
  "bodyType": "Convertible" | "Coupe" | "Estate" | "Hatchback" | "MPV" | "Pickup" | "Saloon" | "SUV" | null,
  "radius": number or null,
  "postcode": string or null,
  "clearAll": boolean,
  "agentResponse": string
}

Filter rules:
- Only set filters the customer explicitly mentioned. Use null for everything not mentioned.
- "clearAll" is true ONLY if the customer says "clear", "reset", "start again", or "show all cars".
- Convert spoken prices: "ten grand" = 10000, "fifteen k" = 15000, "£20,000" = 20000.
- Convert spoken mileage: "50k miles" = 50000, "thirty thousand miles" = 30000.
- Convert spoken radius: "within 20 miles" = 20, "near me" = 25.
- For postcode: only set if customer clearly states a UK postcode.

agentResponse rules:
- 1-2 short sentences spoken aloud on a phone call — natural and conversational.
- Briefly confirm what you understood from the customer.
- Ask exactly ONE follow-up question to narrow the search further.
- Sound warm, friendly, professional — like a real UK car sales agent on the phone.
- Do NOT use technical terms like "filters" — speak naturally.
- Keep it brief — under 30 words.
- Examples: "Perfect, searching for automatic BMWs under ten thousand. Any preference on year or mileage?"
- If clearAll: "No problem at all, I've cleared everything. So, what kind of car are you looking for today?"`;`

  let groqRes;
  try {
    groqRes = await fetch('https://api.groq.com/openai/v1/chat/completions', {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${apiKey}`,
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({
        model: 'llama-3.1-8b-instant',
        messages: [
          { role: 'system', content: systemPrompt },
          ...history
            .filter(h => h && (h.role === 'user' || h.role === 'assistant') && typeof h.content === 'string')
            .map(h => ({ role: h.role, content: h.content.replace(/[<>]/g, '').slice(0, 500) })),
          { role: 'user', content: sanitised }
        ],
        temperature: 0.3,
        max_tokens: 500
      })
    });
  } catch {
    return new Response(JSON.stringify({ error: 'network_error' }), {
      status: 502,
      headers: { 'Content-Type': 'application/json' }
    });
  }

  if (!groqRes.ok) {
    if (groqRes.status === 429) {
      return new Response(JSON.stringify({ error: 'rate_limit' }), {
        status: 429,
        headers: { 'Content-Type': 'application/json' }
      });
    }
    return new Response(JSON.stringify({ error: 'ai_error' }), {
      status: 502,
      headers: { 'Content-Type': 'application/json' }
    });
  }

  let data;
  try {
    data = await groqRes.json();
  } catch {
    return new Response(JSON.stringify({ error: 'ai_parse_error' }), {
      status: 502,
      headers: { 'Content-Type': 'application/json' }
    });
  }

  const content = data.choices?.[0]?.message?.content;
  if (!content) {
    return new Response(JSON.stringify({ error: 'empty_ai_response' }), {
      status: 502,
      headers: { 'Content-Type': 'application/json' }
    });
  }

  let filters;
  try {
    filters = JSON.parse(content);
  } catch {
    // Try to extract JSON object from response if it contains surrounding text
    const match = content.match(/\{[\s\S]*\}/);
    if (match) {
      try {
        filters = JSON.parse(match[0]);
      } catch {
        return new Response(JSON.stringify({ error: 'filter_parse_error' }), {
          status: 502,
          headers: { 'Content-Type': 'application/json' }
        });
      }
    } else {
      return new Response(JSON.stringify({ error: 'filter_parse_error' }), {
        status: 502,
        headers: { 'Content-Type': 'application/json' }
      });
    }
  }

  return new Response(JSON.stringify(filters), {
    status: 200,
    headers: {
      'Content-Type': 'application/json',
      'Cache-Control': 'no-store'
    }
  });
}
