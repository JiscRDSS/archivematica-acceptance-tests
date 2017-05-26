Feature: Identify File Formats during Transfer
  As a researcher, I want all of the files in my dataset to be identified
  and recorded, in order to determine the best preservation actions to take 
  (using rules in the Format Policy Registry) and to help future users of 
  the files. 

Background: Configuration and pre-file identification processing
  Given Archivematica has been configured using standard configuration
    # could be as per processing config steps in premis-events.feature 
    # but I'm thinking of creating a standard-configuration.feature so it is easy to reference (?) 

Scenario Outline: Successful File Identification
  Given a transfer is initiated on directory ~/archivematica-sampledata/SampleTransfers/Images
  When the file identification job is executed
  Then the format of <file_name> is identified as <format> 
  And the formatName, formatVersion and formatRegistry
  And a premis event of type Format Identification is recorded for each file
  And each premis event indicates the program and version number used


  Examples: Files in the Images Transfer
  | file_nanme 	      		                	   | format    | 
  | MARBLES.TGA 	  	                           | fmt/402   | 
  | Vector.NET-Free-Vector-Art-Pack-28-Freedom-Flight.eps  | fmt/124   |
  | oakland03.jp2                                          | fmt/392   |
  | Nemastylis_geminiflora_Flower.PNG                      | fmt/11    |
  | G31DS.TIF                                              | fmt/353   |
  | lion.svg                                               | fmt/91    |
  | WFPC01.GIF 			                           | fmt/4     |
  | BBhelmet.ai					      	   | fmt/19    | 
  | Landing_zone.jpg                                       | fmt/43    |
  | 799px-Euroleague-LE_Roma_vs_Toulouse_IC-27.bmp         | fmt/116   |
  
  
# Test Considerations
  # we want to test confirm file identification happened without relying on 
  # any other downstream processing (so that if a subsequent step fails, 
  # we still know that file ID passed or not). So when writing code to validate the
  # 'then' steps, we don't want to interrogate the AIP.
	 
  # the background is here to ensure that tests can be executed independently as possible
  # i.e. not relying on previous tests to have passed.
