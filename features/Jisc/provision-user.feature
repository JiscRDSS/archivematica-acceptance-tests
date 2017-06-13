Feature: Provision User
  As an RDSS User that has been granted preservation entitlements, 
  I want my Archivematica and Storage Service user accounts 
  to be created automatically when I log in to those systems for the first time. 
  
  # for the moment we have not replicated this gherkin for Storage service
  # the steps are identical - one can read "Archivematica" or "storage service" 
  # interchangeably 
  
Scenario: Preservation User logs in with correct credentials
  Given <user> has an existing account with her identity provider 
    And <user> has the entitlement <entitlement>
    And <user> does NOT have an existing Archivematica user account 
  
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
    And Archivematica creates a user account for <user>
    And <user> is logged in with <role> privileges
    And <user> is presented with the default transfer page 
    
  Examples:
    | user  | username | password | entitlement        | role       |
    | Doug  | dd       | dd12345  | preservation-user  | default    |
    | Enya  | ee       | ee12345  | preservation-admin | admin      |
