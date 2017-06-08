Feature: Authenticate Dashboard User
  As an Archivematica User, I want to login using my existing username and password, 
  so that I can access the dashboard without needing to remember another password.
  
  This features uses the term "Identity Provider" to refer to the instition 
  that provides a user with their account and authentication of their identity.

  # this feature specifies expected behaviour, but we won't automate testing  
  # against a mock. The feature should pass a Gherkin linter but not execute testing
  # with behave.

Scenario: Preservation-User logs in with correct credentials
  Given <user> has an existing account with her identity provider 
    And <user> has the entitlement <entitlement>
    And <user> has an existing Archivematica user account 
    And <user> is not already logged in to Archivematica
  
  When <user> enters (or clicks) a URL for the Archivematica dashboard
    And Archivematica determines <user> is not already logged in
    And Archivematica redirects <user> to the Identity Provider
    And the Identity Provider determines the <user> does not have an existing authenticated session
  
  Then the Identity Provider presents a login page
    And <user> enters their user name <username> and password <password>
    And the Identity Provider authenticates <user>
    And the Identity Provider presents an Information Release consent page
    And <user> selects the option "Ask me again at next login" and clicks "accept"
    And the Identity Provider redirects <user> to Archivematica
    And Archivematica validates the response from the Identity Provider
    And <user> is logged in with <role> privileges
    And <user> is presented with the default transfer page 
    
  Examples:
    | user  | username | password | entitlement        | role       |
    | Alice | aa       | aa12345  | preservation-user  | default    |
    | Bert  | bb       | bb12345  | preservation-admin | admin      |

Scenario: IdP user without credentials attempts login (Charlie)
  Given Charlie has an existing account with his identity provider 
  And Charlie does not have "preservation-user" or "preservation-admin" entitlements
  And Charlie is not already logged in to his identity provider
  
  When Charlie enters (or clicks) a URL for the Archivematica dashboard
  And Archivematica determines Charlie is not already logged in
  And Archivematica redirects Charlie to the Identity Provider
  And the Identity Provider determines Charlie does not have an existing authenticated session
  
  Then the Identity Provider presents a login page
  And Charlie enters his user name and password
  And the Identity Provider authenticates Charlie
  And the Identity Provider presents an Information Release consent page
  And Charlie selects the option "Ask me again at next login" and clicks "accept"
  And the Identity Provider redirects the user back to the dashboard
  And the Charlie is presented with an "Access Denied" page informing them to contact their administrator 
  
Scenario: Preservation-User with existing IdP session logs in (Alice)
  Given Alice has an existing account with her identity provider 
  And Alice has the entitlement "preservation-user"
  And Alice has an existing Archivematica user account 
  And Alice is not already logged in to Archivematic
  And Alice IS logged in with her Identity Provider
  
  When Alice enters (or clicks) a URL for the Archivematica dashboard
  And Archivematica determines Alice is not already logged in
  And Archivematica redirects the user to the Identity Provider
  And the Identity Provider determines Alice already has an existing authenticated session
  
  Then the Identity Provider presents an Information Release consent page
  And Alice selects the option "Ask me again at next login" and clicks "accept"
      # these 2 steps will happen if user has previously chosen to ask for consent 
      # at next login. If user chose to remember consent this step is skipped
  And the Identity Provider redirects Alice to Archivematica
  And Archivematica validates the response from the Identity Provider
  And Alice is logged in with no admin privileges
  And Alice is presented with the default transfer page

# Other Scenarios to be completed: 
#       Existing user attempts to use expired session
#       Authenticated by IdP with correct authorities (eduPersonEntitlement) but does not have AM user account yet
#
# Future additions to existing scenarios:
#   The current implementation is configured to use a single IdP. In future, we will want to support selection
#   of the correct IdP. So a clause along the following lines should be added to these scenarios:
#       When Archivematica asks the user to indicate their Identity Provider
