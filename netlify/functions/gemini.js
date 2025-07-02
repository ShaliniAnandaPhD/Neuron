// This is our secure Netlify Function.
// It runs on Netlify's servers, not in the user's browser.

// The 'fetch' command is available globally in this environment.
// We do NOT need to import it.

exports.handler = async function (event, context) {
  // Only allow POST requests.
  if (event.httpMethod !== 'POST') {
    return { statusCode: 405, body: 'Method Not Allowed' };
  }

  try {
    // Get the API key from the environment variables we set in the Netlify UI.
    // This is the secure part - the key is never exposed to the public.
    const apiKey = process.env.GEMINI_API_KEY;
    const model = "gemini-2.0-flash";
    const apiUrl = `https://generativelanguage.googleapis.com/v1beta/models/${model}:generateContent?key=${apiKey}`;

    // Get the prompt and other data sent from our frontend.
    const requestBody = JSON.parse(event.body);

    // Make the actual call to the Google Gemini API.
    const response = await fetch(apiUrl, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(requestBody), // Pass the payload from the frontend
    });

    if (!response.ok) {
      // If the API call fails, pass the error back to the frontend.
      const errorBody = await response.text();
      console.error('Google API Error:', errorBody);
      return {
        statusCode: response.status,
        body: JSON.stringify({ error: `Google API Error: ${response.statusText}`, details: errorBody }),
      };
    }

    // If the call is successful, get the JSON data.
    const data = await response.json();

    // Return the successful response to our frontend.
    return {
      statusCode: 200,
      body: JSON.stringify(data),
    };
  } catch (error) {
    console.error('Serverless Function Error:', error);
    // If our function has an internal error, return a 500 status.
    return {
      statusCode: 500,
      body: JSON.stringify({ error: 'Internal Server Error' }),
    };
  }
};
