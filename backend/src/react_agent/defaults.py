# Tool dictionaries by service
SERVICE_METHODS = {
    "x": [
        "X_DeleteTweetById",
        "X_LookupSingleUserByUsername",
        "X_LookupTweetById",
        "X_PostTweet",
        "X_SearchRecentTweetsByKeywords",
        "X_SearchRecentTweetsByUsername",
    ],
    "github": [
        "Github_CountStargazers",
        "Github_CreateIssue",
        "Github_CreateIssueComment",
        "Github_CreateReplyForReviewComment",
        "Github_CreateReviewComment",
        "Github_GetPullRequest",
        "Github_GetRepository",
        "Github_ListOrgRepositories",
        "Github_ListPullRequestCommits",
        "Github_ListPullRequests",
        "Github_ListRepositoryActivities",
        "Github_ListReviewCommentsInARepository",
        "Github_ListReviewCommentsOnPullRequest",
        "Github_ListStargazers",
        "Github_SetStarred",
        "Github_UpdatePullRequest",
    ],
    "gmail": [
        "Google_ListDraftEmails",
        "Google_ListEmails",
        "Google_ReplyToEmail",
        "Google_SendEmail",
        "Google_SendDraftEmail",
        "Google_WriteDraftEmail",
        "Google_WriteDraftReplyEmail",
        "Google_SearchContactsByEmail",
        "Google_SearchContactsByName",
    ],
    "google": [
        "Google_ChangeEmailLabels",
        "Google_CreateContact",
        "Google_CreateLabel",
        "Google_DeleteDraftEmail",
        "Google_GetThread",
        "Google_ListEmailsByHeader",
        "Google_ListLabels",
        "Google_ListThreads",
        "Google_SearchContactsByEmail",
        "Google_SearchContactsByName",
        "Google_SearchThreads",
        "Google_TrashEmail",
        "Google_UpdateDraftEmail",
    ],
    "gcal": [
        "Google_SearchContactsByEmail",
        "Google_SearchContactsByName",
        "Google_CreateEvent",
        "Google_ListEvents",
        "Google_UpdateEvent",
        "Google_DeleteEvent",
    ],
    "linkedin": ["Linkedin_CreateTextPost"],
    "search": [
        "Search_SearchGoogle",
    ],
    "hotels": ["Search_SearchHotels"],
    "flights": [
        "Search_SearchOneWayFlights",
        "Search_SearchRoundTripFlights",
    ],
    "stocks": ["Search_StockSummary", "Search_StockHistoricalData"],
    "codesandbox": ["CodeSandbox_RunCode"],
}


def get_tools():
    """Get all tool names from the SERVICE_METHODS dictionary."""
    tool_names = []
    for service, tools in SERVICE_METHODS.items():
        tool_names.extend([t.split("_")[1] for t in tools])
    return tool_names
