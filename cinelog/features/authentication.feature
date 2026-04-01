Feature: User Authentication
    Scenario: Use the login form.
        Given I have an account with user5678@email.com and password.5678
        And I am on the "Log in" page
        When I fill in the "Email" field with "user5678@email.com"
        And I fill in the "Password" field with "password.5678"
        And I submit the form
        Then I should be logged in
        And I should be on the "movies" page

    Scenario: Create an account using signup form.
        Given I am on the "Sign up" page
        When I fill in the "Email" field with "user5678@email.com"
        When I fill in the "Username" field with "user5678"
        And I fill in the "Password" field with "password.5678"
        And I fill in the "Confirm Password" field with "password.5678"
        And I submit the signup form
        Then I should be logged in
        And I should be on the "movies" page

    Scenario: Login with invalid credentials
        Given I have an account with user5678 and password.5678
        And I am on the "Log in" page
        When I fill in the "Email" field with "user5678@email.com"
        And I fill in the "Password" field with the wrong password "1234" instead of "password.5678"
        Then the form will not be submitted


    Scenario: Sign out
        Given I am logged in
        And I click the log out button
        Then I will be logged out
        And redirected to the home page
