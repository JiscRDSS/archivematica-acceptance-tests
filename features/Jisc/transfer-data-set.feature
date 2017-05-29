Feature: Transfer Data Set:
  The preservation system needs to copy the dataset to a storage location where it can 
  carry out preservation processing (in order to ensure that access or updates from RDSS
  users do not interfere with preservation processing). 

Scenario: Successful DataSet Transfer
  Given archivematica_channel_adaptor has received a valid Preservation Request
	# as described by register-preservation-request.feature	
  
  When archivematica_channel_adaptor creates a temporary directory named after (??)
    # in the archivematica_transfer_deposit_dir (as per root.go)
    # directory will be visible in Transfer tab; could be manually processed if there are errors downstream
  And archivematica_channel_adaptor copies each file to the temporary directory
  
  Then archivematica-channel-adaptor calls the archivematica_API to create a transfer
    # as per /api/transfer/start_transfer/ described by https://wiki.archivematica.org/Archivematica_API
  And Archivematica authenticates the call from the archivematica-channel-adaptor
    # see https://github.com/JiscRDSS/archivematica/issues/9 for more detail
  And archivematica-channel-adaptor calls the transfer <name?> (where does this come from?)
    # see data mapping for full details 
  And Archivematica copies the dataset from the temporary directory to a processing directory
  And Archivematica provides a response indicating the copy was successful
  And the Archivematica-channel-adaptor tells archivematica to start the AM Transfer process
    # as per /api/transfer/approve/ described by https://wiki.archivematica.org/Archivematica_API
  And Archivematica applies the default processing configuration
    # currently not working due to: https://github.com/JiscRDSS/archivematica/issues/8
    # later we must add scenarios where an alternative processing configuration is provided with the dataset

# not yet implemented: (although I'm wondering if this should really be done by channel adaptor at all?)   
      # And Archivematica retrieves the Etag checksum for each file 
      # And Archivematica calculates the MD5 checksum for each copied file
      # Archivematica confirms the Etag checksum matches the MD5 checksum for each copied file

# Scope Assumptions for Sprint 3
# I suggest we focus on the above above before addressing any of the below in this sprint
#	a) creating metadata.csv; submission docs etc. covered by Ingest Metadata in Sprint 4  
#	b) large files will need a more complicated fixity check (as per the S3 checksum page on wiki) 
#       c) fixity check of any other checksums provided in MetadataCreate message
#	d) recreating original folder hierarchy... PeterVG commented that required info may come in future version of MetadataCreate message?	 
  
# The following two lines are from Peter's data mapping analysis. Can these wait to "Ingest Metadata" in sprint 4?
# RDSS-Archivematica creates a new archivematica:intellectualEntity metadata record and assigns it a unique archivematica:identifier.
# RDSS-Archivematica reads the property values stored in the rdss:dataset metadata record and writes them a new archivematica:intellectualEntity record using the mappings specified below.

