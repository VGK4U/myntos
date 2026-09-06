export const CANONICAL_API_PATHS = {
    START_JOURNEY: '/staff/journeys/start',
    HEARTBEAT: (journeyId) => `/staff/journeys/${journeyId}/heartbeat`,
    END_JOURNEY: (journeyId) => `/staff/journeys/${journeyId}/end`,
    GET_ACTIVE: '/staff/journeys/active',
    LIST_MY_JOURNEYS: '/staff/journeys/my'
};
//# sourceMappingURL=api-adapter.js.map