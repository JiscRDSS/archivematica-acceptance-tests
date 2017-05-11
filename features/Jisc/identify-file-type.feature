Feature: Identify File Types during Ingest
  As a researcher, I wants all of the files in one of my datasets to be identified
  and recorded.  
  This information is useful for future users of the dataset. 
  This information is also useful to determine the best preservation actions to take
  on each file (using rules in the Format Policy Registry). 

Background: Configuration and pre-file identification processing
  Given Archivematica has been configured using <config_example_1>
  And a transfer has been created from the 'Images' SampleTransfers
  And Transfer processing has completed

Scenario Outline: Successful File Identification
  Given ingest is initiated on the 'Images' transfer
  When the file identification job is executed
  Then a log from the file identification tool is generated for each file
  And a premis event of type Format Identification is recorded for each file
  And the format of <file_name> is identified as <format> 

  Examples: Files in the Images Transfer
  | file_nanme 	      								                	   | format    | 
  | MARBLES.TGA 	  									                     | fmt/402   | 
  | Vector.NET-Free-Vector-Art-Pack-28-Freedom-Flight.eps  | fmt/124   |
  | oakland03.jp2                                          | fmt/392   |
  | Nemastylis_geminiflora_Flower.PNG                      | fmt/11    |
  | G31DS.TIF                                              | fmt/353   |
  | lion.svg                                               | fmt/91    |
  | WFPC01.GIF										                         | fmt/4     |
  | BBhelmet.ai										                    	   | fmt/19    | 
  | Landing_zone.jpg                                       | fmt/43    |
  | 799px-Euroleague-LE_Roma_vs_Toulouse_IC-27.bmp         | fmt/116   |
  
  
# Test Considerations
  # we want to test confirm file identification happened without relying on 
  # any other downstream processing (so that if a subsequent step fails, 
  # we still know that file ID passed or not). So when writing code to validate the
  # 'then' steps, we don't want to interrogate the AIP.
	 
  # the background is here to ensure that tests can be executed independently as possible
  # i.e. not relying on previous tests to have passed.
	 
  # For Jisc MVP automated workflow, there doesn't seem to be much point in 
  # doing file identification at transfer... because we won't hold items in backlog
  # Since we will move straight to ingest you'd only get the same results twice. 
  # This test is therefore written for file identification at ingest. 
