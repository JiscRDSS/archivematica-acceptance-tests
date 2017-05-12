Feature: Register Preservation Request
  As a Research Manager, I want to request that a particular Dataset is sent to Archivematica for preservation
  How the Research Manager triggers this request is a RDSS concern and out-of-scope for the RDSS-Archivematica sub-domain
  Archivematica will subscribe to all MetadataCreate command messages that are sent to the RDSS Message Broker (Amazon Kinesis) 
  The MetadataCreate message will consists of a messageHeader and messageBody that is compliant with rdss-messaging-api-docs
  The MetadataCreate message will contain all the information required by Archivematica to process the request to preserve the Dataset
  Following a successful Register Preservation Request for a given RDSS Dataset, Archivematica will Transfer Files and Ingest Metadata for that Dataset
  Determining if the preservation request contains valid file storage location information or compliant payload metadata is out-of-scope for this feature. Instead, this is dealt with in the Transfer Files and Ingest Metadata features. 
	
Scenario Outline: Valid Preservation Request Received
  Given that Archivematica is subscribed to MetadataCreate messages from the RDSS Message Broker
  And a MetadataCreate message is sent to the RDSS Message Broker by a RDSS application		
  When <Valid RDSS Message criteria>
    # see https://github.com/JiscRDSS/rdss-message-api-docs#message-structure
  Then Archivematica creates a local SYSLOG entry for the valid Register Preservation request.
    # see https://github.com/JiscRDSS/rdss-message-api-docs#logging 
    # e.g. "logger -p local0.info -i "[INFO] Message received"
	
  Examples:
    | Valid RDSS Message criteria                                             |                                         
    | The message is serialized in JSON (JavaScript Object Notation) format   |
    | The message size does not exceed 1000kb                                 |
    | The message contains a messageHeader and a messageBody                  |
    | The value of the messageClass property is equivalent to "Command"       |
    | The value of the messageType property is equivalent to "MetadataCreate" |
    | The value of the messageBody payload property is not null               |
    | The value of objectIdentifierValue is not null                          |
		
Scenario Outline: Invalid Preservation Request (non-compliant message structure) 
  Given a preservation request message is received
  When <Invalid RDSS Message criteria>
    # see https://github.com/JiscRDSS/rdss-message-api-docs#message-structure
  Then Archivematica writes an error entry for that message to the local Invalid Message Queue
    # as per https://github.com/JiscRDSS/rdss-message-api-docs#invalid-message-queue
    # note: currently there is no error code in rdss-messaging-api-docs for non-compliance with message structure (just 004 for invalid headers, maybe expand to include all of the message structure? eg. JSON notation, 1000kb limit).

  Examples:
    | Invalid RDSS Message criteria                                               |
    | The message is not serialized in JSON (JavaScript Object Notation) format   |
    | The message size exceeds 1000kb                                             |
    | The message does not contain a messageHeader or a messageBody section       |
    
Scenario Outline: Invalid Preservation Request (expired message) 
  Given that Archivematica is subscribed to MetadataCreate messages from the RDSS Message Broker
  And a MetadataCreate message is sent to the RDSS Message Broker by a RDSS application	
  When <Invalid RDSS Message criteria>
    # see https://github.com/JiscRDSS/rdss-message-api-docs#message-structure
  Then Archivematica writes an error code QUEUEINVL003 for that message to the local Invalid Message Queue
    # as per https://github.com/JiscRDSS/rdss-message-api-docs#invalid-message-queue
   
  Examples:
    | Invalid RDSS Message criteria                                          |
    | The message expiration date has passed before the message was received |
    
Scenario Outline: Invalid Preservation Request (non-compliant messageBody) 
  Given a preservation request message is received
  When <Invalid RDSS Message criteria>
    # see https://github.com/JiscRDSS/rdss-message-api-docs#message-structure
  Then Archivematica writes an error code QUEUEINVL001 for that message to the local Invalid Message Queue
    # as per https://github.com/JiscRDSS/rdss-message-api-docs#invalid-message-queue

  Examples:
    | Invalid RDSS Message criteria                                                 |
    | The messageBody payload content validates against a known RDSS message schema |                           
    | The value of the messageBody payload property is null                         |
    | The value of objectIdentifierValue is null                                    |
    
Scenario Outline: Invalid Preservation Request (unsupported messageType) 
  Given a preservation request message is received
  When <Invalid RDSS Message criteria>
    # see https://github.com/JiscRDSS/rdss-message-api-docs#message-structure
  Then Archivematica writes an error code QUEUEINVL002 for that message to the local Invalid Message Queue
    # as per https://github.com/JiscRDSS/rdss-message-api-docs#invalid-message-queue

  Examples:
    | Invalid RDSS Message criteria                                               |
    | The value of the messageClass property is not equivalent to "Command"       |
    | The value of the messageType property is not equivalent to "MetadataCreate" |
 
