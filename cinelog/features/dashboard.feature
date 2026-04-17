Feature: Dashboard statistics
    Scenario: When a logged-in user navigates to the Statistics page, their personal movie statistics are displayed.
        Given I have an account with "user5678@email.com", "user5678", and "password.5678"
        And I am on the dashboard page
        Then I should see statistics about my movies
    
    Scenario: The statistics page shows key metrics.
        Given I have an account with "user5678@email.com", "user5678", and "password.5678"
        And I am on the dashboard page
        Then I should see a statistic for movies logged
        And a statistic for total hours logged
        And a statistic for average rating
        And a statistic for most watched genre

    Scenario: Statistics automatically update when a user logs or edits a movie entry.
        Given I have an account with "user5678@email.com", "user5678", and "password.5678"
        When I add a new movie to my watchlist
        Then I should see the total watchlist movie count increase by 1
