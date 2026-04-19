# Service: `subscription`

**7 methods** in this service.

## `GET /subscription/v1/getAllSubscriptions`
**Operation:** `getAllSubscriptions`

**Summary:** Get all subscriptions

**Description:** Use this method to retrieve multiple subscriptions. If you do not specify the userStringId parameter, then it returns all subscriptions that were created by the user. If a userStringId is specified, it will return only those subscriptions which are stored with a userStringId that is an exact match.

**Parameters:**
- `sessionId` (header, required) — session token
- `userStringId` (query, optional) — user-defined keyword string to (exact) match on

**Responses:**
- `200` — successful operation → `SubscriptionResponse`
- `401` — the sessionId is not provided or has expired, obtain a new sessionId and try again → _(no schema)_
- `403` — the web service user credentials used to create the sessionId do not have access to the → _(no schema)_
- `500` — the server encountered an error and could not proceed with the request → _(no schema)_

---

## `GET /subscription/v1/getEvents`
**Operation:** `getEvents`

**Summary:** Get events from the event stream

**Description:** Use this method to retrieve events starting at a specific point within the event stream.

**Parameters:**
- `sessionId` (header, required) — session token
- `subscriptionId` (query, required) — ID of the subscription to use when retrieving events
- `replayId` (query, required) — the starting point in the event stream for retrieving events
- `numberOfEvents` (query, optional) — the number of events to retrieve. If you would like to retrieve events in the past, you can specify a replayId in the past and use numberOfEvents to retrieve specified number of events.

**Responses:**
- `200` — successful operation → `SubscriptionEventResponse`
- `400` — the request is not properly formatted or does not include required parameters → _(no schema)_
- `401` — the sessionId is not provided or has expired, obtain a new sessionId and try again → _(no schema)_
- `403` — the web service user credentials used to create the sessionId do not have access to the → _(no schema)_
- `500` — the server encountered an error and could not proceed with the request → _(no schema)_

---

## `GET /subscription/v1/getNewEvents`
**Operation:** `getNewEvents`

**Summary:** Get new events from the event stream

**Description:** Use this method to retrieve all events using the replayId stored in the subscription record. Calling this method should give you only those events that you have not processed before.

**Parameters:**
- `sessionId` (header, required) — session token
- `subscriptionId` (query, required) — ID of the subscription to use when retrieving events
- `numberOfEvents` (query, optional) — the number of events to retrieve

**Responses:**
- `200` — successful operation → `SubscriptionEventResponse`
- `400` — the request is not properly formatted or does not include required parameters → _(no schema)_
- `401` — the sessionId is not provided or has expired, obtain a new sessionId and try again → _(no schema)_
- `403` — the web service user credentials used to create the sessionId do not have access to the → _(no schema)_
- `500` — the server encountered an error and could not proceed with the request → _(no schema)_

---

## `GET /subscription/v1/getSubscription`
**Operation:** `getSubscription`

**Summary:** Get a subscription by its ID

**Description:** Use this method to retrieve a single subscription using its unique identifier.

**Parameters:**
- `sessionId` (header, required) — session token
- `subscriptionId` (query, required) — ID of the subscription to retrieve

**Responses:**
- `200` — successful operation → `SubscriptionResponse`
- `400` — the request is not properly formatted or does not include required parameters → _(no schema)_
- `401` — the sessionId is not provided or has expired, obtain a new sessionId and try again → _(no schema)_
- `403` — the web service user credentials used to create the sessionId do not have access to the → _(no schema)_
- `500` — the server encountered an error and could not proceed with the request → _(no schema)_

---

## `POST /subscription/v1/appendFilter`
**Operation:** `appendFilter`

**Summary:** Add filters to the subscription

**Description:** This method adds more filters to the subscription, which in turn allows a single subscription to return events from multiple object classes. The 'excludes' parameter is an array. Even if you only have one attribute name, you must pass it as an array of string with a single element. The 'clientId' parameter is optional only when the user parameter is configured without a restriction on the client. See the Authentication and Authorization section of the online documentation for further detail. The 'userStringId' parameter was designed so that multiple subscriptions could be created that share th…

**Parameters:**
- `sessionId` (header, required) — session token

**Responses:**
- `200` — successful operation → `SubscriptionResponse`
- `400` — the request is not properly formatted or does not include required parameters → _(no schema)_
- `401` — the sessionId is not provided or has expired, obtain a new sessionId and try again → _(no schema)_
- `403` — the web service user credentials used to create the sessionId do not have access to the → _(no schema)_
- `422` — unprocessable content → _(no schema)_
- `500` — the server encountered an error and could not proceed with the request → _(no schema)_

---

## `POST /subscription/v1/cancelSubscription`
**Operation:** `cancelSubscription`

**Summary:** Remove subscription

**Description:** Use this method to remove a subscription completely. Note that there is no means to delete individual filters. You would need to delete the subscription entirely and then create a new one with the filters that you require.

**Parameters:**
- `sessionId` (header, required) — session token

**Request body:**
- Content-Type: `application/x-www-form-urlencoded`
- Required fields: `subscriptionId`

**Responses:**
- `200` — successful operation → `CancelSubscriptionResponse`
- `400` — the request is not properly formatted or does not include required parameters → _(no schema)_
- `401` — the sessionId is not provided or has expired, obtain a new sessionId and try again → _(no schema)_
- `403` — the web service user credentials used to create the sessionId do not have access to the → _(no schema)_
- `422` — unprocessable content → _(no schema)_
- `500` — the server encountered an error and could not proceed with the request → _(no schema)_

---

## `POST /subscription/v1/createSubscription`
**Operation:** `createSubscription`

**Summary:** Create new subscription

**Description:** Use this method to create a new event subscription and its initial filter. There are some important notes and restrictions regarding the input parameters. The 'excludes' parameter is an array. Even if you only have one attribute name, you must pass it as an array of string with a single element. The 'clientId' parameter is optional only when the user parameter is configured without a restriction on the client. See the Authentication and Authorization section of the online documentation for further detail. The 'userStringId' parameter was designed so that multiple subscriptions could be created…

**Parameters:**
- `sessionId` (header, required) — session token

**Responses:**
- `200` — successful operation → `SubscriptionResponse`
- `400` — the request is not properly formatted or does not include required parameters → _(no schema)_
- `401` — the sessionId is not provided or has expired, obtain a new sessionId and try again → _(no schema)_
- `403` — the web service user credentials used to create the sessionId do not have access to the → _(no schema)_
- `422` — unprocessable content → _(no schema)_
- `500` — the server encountered an error and could not proceed with the request → _(no schema)_

---
