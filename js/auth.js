export default class Auth {

  constructor(domain) {
    this.domain = domain

    // Check to see if we're redirecting back
    // from an authorization with a code.
    const url = new URL(window.location);
    if (url.searchParams.has('code')) {

      // Get the code and strip it out of the URL
      const code = url.searchParams.get('code')
      url.searchParams.delete('code')
      url.searchParams.delete('state')
      window.history.replaceState({}, '', url);

      // Exchange it for a token
      this.codeToToken(code)

    } else {
      // Initiate authorization
      this.authorize()
    }
  }

  async authorize() {
    // Send a warning alert
    alert(
      `This application requires access to your account on ${this.domain}.
      \n\nClick OK to continue to the authorization page.`
    )

    // Generate a random client secret
    const clientSecret = Math.random().toString(36).substr(2)

    // The client ID is the secret's hex hash
    const encoder = new TextEncoder()
    const clientSecretData = encoder.encode(clientSecret)
    const clientIDBuffer = await crypto.subtle.digest('SHA-256', clientSecretData)
    const clientIDArray = Array.from(new Uint8Array(clientIDBuffer))
    const clientID = clientIDArray.map(b => b.toString(16).padStart(2, '0')).join('')

    // Store the client ID and secret in a cookie
    document.cookie = `clientSecret=${clientSecret}; SameSite=Strict`
    document.cookie = `clientID=${clientID}; SameSite=Strict`

    // Open the login window
    const redirectURI = encodeURIComponent(window.location)
    window.location.replace(`https://${this.domain}/auth?client_id=${clientID}&redirect_uri=${redirectURI}&state=null`)
  }

  getAndDeleteCookie(param) {
    // Decode the cookie string
    const decodedCookies = decodeURIComponent(document.cookie);

    // Delete the cookie if ey exists
    document.cookie = param + '=; max-age=0; SameSite=Strict'

    // Find the cookie if it exists
    for (const cookie of decodedCookies.split(';')) {
      // Trim off white-space and parse
      const paramMap = cookie.trim().split(param + '=')
      if (paramMap.length > 1) return paramMap[1]
    }
  }

  authorizationError(reason) {
    alert(`Authorization Error: ${reason}\n\nClick OK to reload.`)
    window.location.reload()
  }

  async codeToToken(code) {
    // Read the stored client cookies
    const clientSecret = this.getAndDeleteCookie('clientSecret')
    const clientID     = this.getAndDeleteCookie('clientID')

    // Make sure they actually exist
    if (!clientSecret || !clientID) {
      return this.authorizationError("missing client secret - are cookies enabled?")
    }

    // Construct the body of the POST
    let form = new FormData();
    form.append('client_id', clientID)
    form.append('client_secret', clientSecret)
    form.append('code', code)

    // Ask to exchange the code for a token
    const response = await fetch(`https://${this.domain}/token`, {
        method: 'post',
        body: form
    })

    // Make sure the response is OK
    if (!response.ok) {
      let reason = response.status + ": "
      try {
        reason += (await response.json()).detail
      } catch (e) {
        reason += response.statusText
      }

      return this.authorizationError(`could not exchange code for token.\n\n${reason}`)
    }

    // Parse out the token
    const data = await response.json()
    this.token = data.access_token

    // And make sure that the token is valid
    if (!this.token) {
      return this.authorizationError("could not parse token.")
    } else {
      alert("Authorized!")
    }

  }

  async request(method, path, params) {
    // If the token doesn't already exist wait for it
    while (!this.token) {
      await new Promise(resolve => setTimeout(resolve, 100));
    }

    // Send the request to the server
    const paramsString = (new URLSearchParams(params)).toString()
    const response = await fetch(`https://${this.domain}/${path}?${paramsString}`, {
      method: method,
      headers: new Headers({
        'Authorization': 'Bearer ' + this.token
      }),
    })

    // Make sure it went OK
    if (!response.ok) {
      let reason = response.status + ": "
      try {
        reason += (await response.json()).detail
      } catch (e) {
        reason += response.statusText
      }

      throw new Error(reason)
    }

    return await response.json()
  }

}
