  pull_request_review:
    types:
      - submitted

  schedule:
    - cron: '*/5 * * * *'


            # Step 2: Mark PR as review-ready (undraft)
            echo "  Marking PR #$pr_number as $READY_FOR_CODE_REVIEW_LABEL"
            pr_node_id=$(gh api "repos/${{ github.repository }}/pulls/$pr_number" --jq '.node_id' 2>&1) || {
              echo "::error::Failed to get node_id for PR #$pr_number: $pr_node_id"
              continue
            }
            output=$(gh api graphql \
              -f query='mutation($pullRequestId: ID!) { markPullRequestReadyForReview(input: {pullRequestId: $pullRequestId}) { pullRequest { number isDraft } } }' \
              -f pullRequestId="$pr_node_id" 2>&1) || echo "::error::Failed to mark PR #$pr_number as ready via API: $output"

            # Step 3: Add Copilot as a reviewer
            echo "  Adding copilot-swe-agent[bot] as requested reviewer on PR #$pr_number"
            reviewer_response_file=$(mktemp)
            reviewer_status=$(curl -sS \
              -o "$reviewer_response_file" \
              -w "%{http_code}" \
              -X POST \
              -H "Accept: application/vnd.github+json" \
              -H "Authorization: Bearer $GH_TOKEN" \
              -H "X-GitHub-Api-Version: 2022-11-28" \
              "${{ github.api_url }}/repos/${{ github.repository }}/pulls/$pr_number/requested_reviewers" \
              -d '{"reviewers":["copilot-swe-agent[bot]"]}' 2>&1)
            if ! [[ "$reviewer_status" =~ ^2 ]]; then
              output=$(cat "$reviewer_response_file")
              echo "::error::Failed to add copilot-swe-agent[bot] as requested reviewer to PR #$pr_number: HTTP $reviewer_status $output"
            fi
            rm -f "$reviewer_response_file"
