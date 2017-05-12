Feature: Transfer Data Set:
  The preservation system needs to copy the dataset to local storage 
  in order to carry out preservation processing. 

Scenario: Successful Transfer
  Given Archivematica confirms receipt of a Preservation Request
	# i.e. (currently) a MetadataCreate message	
  When Archivematica initiates the transfer of the dataset
  Then Archivematica creates a new directory called <??> to store the dataset
  And Archivematica copies each file listed in the MetadataCreate message to <??>
  And Archivematica performs a fixity check using the file's Etag to confirm a successful transfer
     # we could break this step down more if it helps... e.g.   
  	 # Archivematica retrieves the Etag checksum for each file 
  	 # Archivematica calculates the MD5 checksum for the copied file
  	 # Archivematica confirms the Etag checksum matches the MD5 checksum
  And Archivematica -- creates a log entry confirming successful transfer (???)
  	 # ultimately this info should go in METS file? but maybe we just do a simple log for now? 	
  	    
# Scope Assumptions for Sprint 3
# I suggest we focus on the above above before addressing any of the below in this sprint
#	a) creating metadata.csv; submission docs etc. covered by Ingest Metadata in Sprint 4  
#	b) large files will need a more complicated fixity check (as per the S3 checksum page on wiki) 
# c) fixity check of any other checksums provided in MetadataCreate message
#	d) recreating original folder hierarchy... PeterVG commented that required info may come in future version of MetadataCreate message?	 
  
# The following two lines are from Peter's data mapping analysis. Can these wait to "Ingest Metadata" in sprint 4?
# RDSS-Archivematica creates a new archivematica:intellectualEntity metadata record and assigns it a unique archivematica:identifier.
# RDSS-Archivematica reads the property values stored in the rdss:dataset metadata record and writes them a new archivematica:intellectualEntity record using the mappings specified below.

